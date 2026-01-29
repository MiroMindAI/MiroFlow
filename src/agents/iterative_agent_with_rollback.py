# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Iterative Agent - with tool calling capability and rollback retry mechanism

Supports automatic rollback retry when LLM output is truncated or malformed.
"""

from __future__ import annotations

from omegaconf import DictConfig
from typing import Callable, Awaitable, Tuple, List

from src.logging.task_tracer import get_tracer

from src.registry import register, ComponentType
from src.agents.base import BaseAgent
from src.agents.context import AgentContext
from src.agents.sequential_agent import SequentialAgent

AgentCaller = Callable[[str, dict], Awaitable[str]]

# MCP tags - if these appear in response but no tool calls are parsed, indicates format error/truncation
MCP_TAGS = [
    "<use_mcp_tool>",
    "</use_mcp_tool>",
    "<server_name>",
    "</server_name>",
    "<arguments>",
    "</arguments>",
]


@register(ComponentType.AGENT, "IterativeAgentWithToolAndRollback")
class IterativeAgentWithToolAndRollback(BaseAgent):
    """Iterative agent with tool calling capability, supports rollback retry mechanism"""

    def __init__(self, cfg: DictConfig):
        super().__init__(cfg=cfg)

        self.input_processor = SequentialAgent(
            modules=[
                self.create_sub_module(module_cfg)
                for module_cfg in self.cfg.get("input_processor", [])
            ]
        )
        self.output_processor = SequentialAgent(
            modules=[
                self.create_sub_module(module_cfg)
                for module_cfg in self.cfg.get("output_processor", [])
            ]
        )

        # Rollback config - read from yaml, default is 3
        self.max_consecutive_rollbacks = self.cfg.get("max_consecutive_rollbacks", 3)

    def _should_rollback(
        self, llm_output, tool_calls: List, response_text: str
    ) -> Tuple[bool, str]:
        """
        Determine whether rollback retry is needed

        Conditions (by priority):
        1. If there are tool calls, no rollback needed (normal flow)
        2. finish_reason == "length" - API explicitly tells us it was truncated (100% reliable)
        3. Response has MCP tags but no tool calls parsed - incomplete format (100% reliable)
        4. Other cases are treated as normal completion

        Args:
            llm_output: LLM output object
            tool_calls: List of parsed tool calls
            response_text: LLM response text

        Returns:
            (should_rollback, reason) - whether rollback is needed and the reason
        """
        # 1. If there are tool calls, no rollback needed
        if tool_calls:
            return False, "has_tool_calls"

        # 2. Check finish_reason == "length" (100% reliable)
        # This is a flag returned by the API, explicitly indicating the response was truncated
        try:
            if (
                llm_output.raw_response
                and llm_output.raw_response.choices
                and len(llm_output.raw_response.choices) > 0
                and llm_output.raw_response.choices[0].finish_reason == "length"
            ):
                return True, "finish_reason_length"
        except (AttributeError, IndexError):
            pass  # raw_response structure doesn't match expected, skip this check

        # 3. Check if response has MCP tags but no tool calls parsed (format error/truncated)
        # This means the model wanted to call tools, but the XML is incomplete
        if any(tag in response_text for tag in MCP_TAGS):
            return True, "mcp_tag_without_tool_calls"

        # 4. Normal completion - no tool calls and no anomalies, model considers task complete
        return False, "normal_completion"

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        tracer = get_tracer()
        tracer.save_agent_states(self.name, states={"input_ctx": ctx})

        if ctx.get("message_history") is None:
            input_processor_output = await self.input_processor.run(
                AgentContext(**ctx, mcp_server_definitions=self.mcp_server_definitions)
            )
            initial_user_message = input_processor_output.get(
                "initial_user_message", None
            )
            system_prompt = input_processor_output.get("system_prompt", None)
            if system_prompt is None or initial_user_message is None:
                raise ValueError("system_prompt and initial_user_message are required")
            message_history = [{"role": "user", "content": initial_user_message}]
        else:
            message_history = ctx["message_history"]
            input_processor_output = None

        turn_count = 0
        max_turns = self.cfg.get("max_turns", -1)
        task_failed = False

        # Rollback related variables
        consecutive_rollbacks = 0

        while max_turns == -1 or turn_count < max_turns:
            turn_count += 1

            # LLM call
            llm_output = await self.llm_client.create_message(
                system_prompt=system_prompt,
                message_history=message_history,
                tool_definitions=self.tool_definitions,
            )

            if llm_output.is_invalid:
                task_failed = True
                break

            message_history.append(llm_output.assistant_message)
            tracer.save_agent_states(
                self.name, states={"input_ctx": ctx, "message_history": message_history}
            )

            # Tool calls
            tool_and_sub_agent_calls = self.llm_client.extract_tool_calls_info(
                llm_output.raw_response, llm_output.response_text
            )[0]

            # Check if rollback is needed
            should_rollback, rollback_reason = self._should_rollback(
                llm_output, tool_and_sub_agent_calls, llm_output.response_text
            )

            if len(tool_and_sub_agent_calls) == 0:
                if (
                    should_rollback
                    and consecutive_rollbacks < self.max_consecutive_rollbacks
                ):
                    # Execute rollback: undo this turn's assistant message
                    message_history.pop()
                    turn_count -= 1  # Don't count this turn
                    consecutive_rollbacks += 1
                    tracer.log(
                        f"Rollback #{consecutive_rollbacks}: {rollback_reason}, "
                        f"max={self.max_consecutive_rollbacks}"
                    )
                    continue  # Retry this turn
                else:
                    # Normal completion or max rollback count reached
                    if consecutive_rollbacks >= self.max_consecutive_rollbacks:
                        tracer.log(
                            f"Max rollbacks reached ({self.max_consecutive_rollbacks}), "
                            f"proceeding to summary"
                        )
                    break
            else:
                # Has tool calls, reset rollback counter
                consecutive_rollbacks = 0

                tool_calls = [
                    call
                    for call in tool_and_sub_agent_calls
                    if (
                        "agent-worker" not in call["server_name"]
                        and "skills-worker" not in call["server_name"]
                    )
                ]
                sub_agent_calls = [
                    call
                    for call in tool_and_sub_agent_calls
                    if "agent-worker" in call["server_name"]
                ]
                skill_calls = [
                    call
                    for call in tool_and_sub_agent_calls
                    if "skills-worker" in call["server_name"]
                ]

                (
                    tool_results,
                    tool_calls_exceeded,
                ) = await self.tool_manager.execute_tool_calls_batch(tool_calls)

                # Only execute skill calls if skill_manager exists
                if hasattr(self, "skill_manager"):
                    (
                        skill_results,
                        _skill_calls_exceeded,
                    ) = await self.skill_manager.execute_skill_calls_batch(skill_calls)
                else:
                    skill_results, _skill_calls_exceeded = [], False

                sub_agent_results = await self.run_sub_agents_as_mcp_tools(
                    sub_agent_calls
                )
                all_call_results = self.tool_manager.format_tool_results(
                    tool_results + sub_agent_results + skill_results
                )

            user_msg = self.llm_client.get_user_msg_from_tool_call(
                all_call_results, tool_calls_exceeded
            )
            message_history.append(user_msg)
            tracer.save_agent_states(
                self.name, states={"input_ctx": ctx, "message_history": message_history}
            )

        output_processor_result = await self.output_processor.run(
            AgentContext(
                **ctx, message_history=message_history, task_failed=task_failed
            )
        )
        tracer.save_agent_states(
            self.name,
            states={
                "message_history": message_history,
                "summary_prompt": output_processor_result.get("summary_prompt", None),
                "summary": output_processor_result.get("summary", None),
            },
        )
        return AgentContext(
            message_history=message_history,
            summary=output_processor_result.get("summary", None),
            final_boxed_answer=output_processor_result.get("final_boxed_answer", None),
            exceed_max_turn_summary=output_processor_result.get(
                "exceed_max_turn_summary", None
            ),
        )
