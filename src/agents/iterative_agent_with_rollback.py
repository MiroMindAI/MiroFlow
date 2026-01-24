# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
迭代式 Agent - 带工具调用能力和 Rollback 重试机制

当 LLM 输出被截断或格式错误时，支持自动 rollback 重试。
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

# MCP 标签 - 如果这些出现在响应中但没有被解析成 tool calls，说明格式错误/被截断
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
    """迭代式带工具调用的 Agent，支持 Rollback 重试机制"""

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

        # Rollback 配置 - 从 yaml 读取，默认值为 3
        self.max_consecutive_rollbacks = self.cfg.get("max_consecutive_rollbacks", 3)

    def _should_rollback(
        self, llm_output, tool_calls: List, response_text: str
    ) -> Tuple[bool, str]:
        """
        判断是否需要 rollback 重试

        判断条件（按优先级）：
        1. 如果有 tool calls，不需要 rollback（正常流程）
        2. finish_reason == "length" - API 明确告诉我们被截断了（100% 可靠）
        3. 响应中有 MCP 标签但没解析出 tool calls - 格式不完整（100% 可靠）
        4. 其他情况视为正常结束

        Args:
            llm_output: LLM 输出对象
            tool_calls: 解析出的 tool calls 列表
            response_text: LLM 响应文本

        Returns:
            (should_rollback, reason) - 是否需要 rollback 及原因
        """
        # 1. 如果有 tool calls，不需要 rollback
        if tool_calls:
            return False, "has_tool_calls"

        # 2. 检查 finish_reason == "length"（100% 可靠）
        # 这是 API 返回的标志，明确表示响应被截断
        try:
            if (
                llm_output.raw_response
                and llm_output.raw_response.choices
                and len(llm_output.raw_response.choices) > 0
                and llm_output.raw_response.choices[0].finish_reason == "length"
            ):
                return True, "finish_reason_length"
        except (AttributeError, IndexError):
            pass  # raw_response 结构不符合预期，跳过这个检查

        # 3. 检查响应中有 MCP 标签但没解析出 tool calls（格式错误/被截断）
        # 这说明模型想调用工具，但 XML 不完整
        if any(tag in response_text for tag in MCP_TAGS):
            return True, "mcp_tag_without_tool_calls"

        # 4. 正常结束 - 没有 tool calls 且没有异常情况，说明模型认为任务完成了
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

        # Rollback 相关变量
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

            # 检查是否需要 rollback
            should_rollback, rollback_reason = self._should_rollback(
                llm_output, tool_and_sub_agent_calls, llm_output.response_text
            )

            if len(tool_and_sub_agent_calls) == 0:
                if (
                    should_rollback
                    and consecutive_rollbacks < self.max_consecutive_rollbacks
                ):
                    # 执行 rollback：撤销这一轮的 assistant message
                    message_history.pop()
                    turn_count -= 1  # 不计入这一轮
                    consecutive_rollbacks += 1
                    tracer.log(
                        f"Rollback #{consecutive_rollbacks}: {rollback_reason}, "
                        f"max={self.max_consecutive_rollbacks}"
                    )
                    continue  # 重试这一轮
                else:
                    # 正常结束或达到最大 rollback 次数
                    if consecutive_rollbacks >= self.max_consecutive_rollbacks:
                        tracer.log(
                            f"Max rollbacks reached ({self.max_consecutive_rollbacks}), "
                            f"proceeding to summary"
                        )
                    break
            else:
                # 有 tool calls，重置 rollback 计数器
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
                "summary": output_processor_result.get("summary", None),
            },
        )
        return AgentContext(
            message_history=message_history,
            summary=output_processor_result.get("summary", None),
            final_boxed_answer=output_processor_result.get("final_boxed_answer", None),
        )
