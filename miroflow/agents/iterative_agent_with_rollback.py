# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Iterative Agent - with tool calling capability and rollback retry mechanism

Supports automatic rollback retry when LLM output is truncated or malformed.
"""

from __future__ import annotations

import json
from collections import defaultdict

from omegaconf import DictConfig
from typing import Callable, Awaitable, Tuple, List

from miroflow.logging.task_tracer import get_tracer
from miroflow.llm.base import ContextLimitError

from miroflow.registry import register, ComponentType
from miroflow.agents.base import BaseAgent
from miroflow.agents.context import AgentContext
from miroflow.agents.sequential_agent import SequentialAgent

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

# Refusal keywords - if model outputs these without tool calls, it's refusing to act
REFUSAL_KEYWORDS = [
    "time constraint",
    "I'm sorry, but I can't",
    "I'm sorry, I cannot solve",
    "I cannot continue",
    "I'm unable to",
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

        # Rollback config - read from yaml, default is 5
        self.max_consecutive_rollbacks = self.cfg.get("max_consecutive_rollbacks", 5)
        self.max_duplicate_rollbacks = self.cfg.get("max_duplicate_rollbacks", 3)
        self.verbose = self.cfg.get("verbose", False)

    @staticmethod
    def _get_query_key(tool_call: dict) -> str:
        """Generate a dedup key from a tool call: server_name:tool_name:sorted_arguments_json"""
        return (
            f"{tool_call['server_name']}:{tool_call['tool_name']}:"
            f"{json.dumps(tool_call.get('arguments', {}), sort_keys=True)}"
        )

    def _check_duplicate_tool_calls(
        self, tool_calls: list, used_queries: dict
    ) -> Tuple[bool, str]:
        """Check if any tool call in the list is a duplicate of a previously executed query.

        Returns:
            (has_duplicate, duplicate_info_str)
        """
        for call in tool_calls:
            key = self._get_query_key(call)
            if used_queries.get(key, 0) > 0:
                return True, (
                    f"{call['tool_name']}"
                    f"({json.dumps(call.get('arguments', {}), ensure_ascii=False)[:100]})"
                )
        return False, ""

    def _should_rollback(
        self, llm_output, tool_calls: List, response_text: str
    ) -> Tuple[bool, str]:
        """
        Determine whether rollback retry is needed

        Conditions (by priority):
        1. If there are tool calls, no rollback needed (normal flow)
        2. finish_reason == "length" - API explicitly tells us it was truncated (100% reliable)
        3. Response has MCP tags but no tool calls parsed - incomplete format (100% reliable)
        4. Response contains refusal keywords - model is refusing to act
        5. Other cases are treated as normal completion

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

        # 4. Check for refusal keywords - model is refusing to continue working
        if any(keyword in response_text for keyword in REFUSAL_KEYWORDS):
            return True, "refusal_detected"

        # 5. Normal completion - no tool calls and no anomalies, model considers task complete
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
        reached_limit = False  # Track if agent hit max turns or context limit

        # Pre-render summary prompt for proactive context limit checking
        _summary_prompt_for_context_check = ""
        if self.llm_client.max_context_length > 0:
            try:
                _summary_prompt_for_context_check = self.prompt_manager.render_prompt(
                    "summarize_prompt",
                    context=dict(
                        task_description=ctx.get("task_description", ""),
                        task_failed=False,
                    ),
                )
            except Exception:
                _summary_prompt_for_context_check = ""

        # Rollback related variables
        consecutive_rollbacks = 0
        used_queries = defaultdict(int)  # query_key -> execution count
        duplicate_rollbacks = 0

        while max_turns == -1 or turn_count < max_turns:
            turn_count += 1

            if self.verbose:
                print(f"\n{'='*60}")
                print(f"[Turn {turn_count}] Starting (max_turns={max_turns})")
                print(f"{'='*60}")

            # LLM call (with ContextLimitError fallback)
            try:
                llm_output = await self.llm_client.create_message(
                    system_prompt=system_prompt,
                    message_history=message_history,
                    tool_definitions=self.tool_definitions,
                )
            except ContextLimitError:
                tracer.log(
                    f"ContextLimitError caught at turn {turn_count}, "
                    f"breaking to generate summary"
                )
                reached_limit = True
                break

            if self.verbose:
                usage = getattr(llm_output, "usage", None)
                if usage:
                    print(
                        f"[Turn {turn_count}] LLM returned | "
                        f"prompt_tokens={getattr(usage, 'prompt_tokens', '?')}, "
                        f"completion_tokens={getattr(usage, 'completion_tokens', '?')}"
                    )
                else:
                    print(f"[Turn {turn_count}] LLM returned (no usage info)")
                resp_preview = (llm_output.response_text or "")[:200]
                print(f"[Turn {turn_count}] Response preview: {resp_preview}")

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

            if self.verbose and tool_and_sub_agent_calls:
                print(
                    f"[Turn {turn_count}] Tool calls ({len(tool_and_sub_agent_calls)}):"
                )
                for i, call in enumerate(tool_and_sub_agent_calls):
                    args_preview = json.dumps(
                        call.get("arguments", {}), ensure_ascii=False
                    )[:150]
                    print(
                        f"  [{i+1}] {call.get('server_name', '?')}::{call.get('tool_name', '?')} "
                        f"args={args_preview}"
                    )

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
                    if self.verbose:
                        print(
                            f"[Turn {turn_count}] ROLLBACK #{consecutive_rollbacks}: "
                            f"reason={rollback_reason}, "
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
                # Separate call types first
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

                # Check for duplicate queries (only regular tool calls)
                has_dup, dup_info = self._check_duplicate_tool_calls(
                    tool_calls, used_queries
                )
                if has_dup:
                    if duplicate_rollbacks < self.max_duplicate_rollbacks:
                        message_history.pop()
                        turn_count -= 1
                        duplicate_rollbacks += 1
                        tracer.log(
                            f"Duplicate query rollback #{duplicate_rollbacks}: "
                            f"{dup_info}, max={self.max_duplicate_rollbacks}"
                        )
                        continue
                    else:
                        tracer.log(
                            f"Allowing duplicate after {duplicate_rollbacks} "
                            f"rollbacks: {dup_info}"
                        )

                # Passed all checks, reset rollback counters
                consecutive_rollbacks = 0
                duplicate_rollbacks = 0

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

                if self.verbose:
                    print(
                        f"[Turn {turn_count}] Tool results: "
                        f"{len(tool_results)} tool, "
                        f"{len(sub_agent_results)} sub-agent, "
                        f"{len(skill_results)} skill"
                    )
                    for r in tool_results:
                        result_preview = (
                            str(r.get("result", ""))[:200]
                            if isinstance(r, dict)
                            else str(r)[:200]
                        )
                        print(f"  -> {result_preview}")

                # Record executed queries for duplicate detection
                for call in tool_calls:
                    used_queries[self._get_query_key(call)] += 1

            user_msg = self.llm_client.get_user_msg_from_tool_call(
                all_call_results, tool_calls_exceeded
            )
            message_history.append(user_msg)
            tracer.save_agent_states(
                self.name, states={"input_ctx": ctx, "message_history": message_history}
            )

            # Proactive context limit check
            if _summary_prompt_for_context_check:
                can_continue, message_history = self.llm_client.ensure_summary_context(
                    message_history, _summary_prompt_for_context_check
                )
                if not can_continue:
                    tracer.log(
                        f"Context limit approaching at turn {turn_count}, "
                        f"breaking to generate summary"
                    )
                    reached_limit = True
                    break

        # Check if we exited due to reaching max turns
        if max_turns != -1 and turn_count >= max_turns:
            reached_limit = True

        output_processor_result = await self.output_processor.run(
            AgentContext(
                **ctx,
                message_history=message_history,
                task_failed=task_failed,
                reached_limit=reached_limit,
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
        if self.verbose:
            final_answer = output_processor_result.get("final_boxed_answer", None)
            print(f"\n{'='*60}")
            print(
                f"[DONE] Total turns: {turn_count} | "
                f"task_failed={task_failed} | reached_limit={reached_limit}"
            )
            print(f"[DONE] Final answer: {str(final_answer)[:300]}")
            print(f"{'='*60}\n")

        return AgentContext(
            message_history=message_history,
            summary=output_processor_result.get("summary", None),
            final_boxed_answer=output_processor_result.get("final_boxed_answer", None),
            exceed_max_turn_summary=output_processor_result.get(
                "exceed_max_turn_summary", None
            ),
        )
