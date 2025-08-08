# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import datetime
import sys
import time
import uuid
import re
from typing import Any

from omegaconf import DictConfig
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from miroflow.contrib.tracing import function_span, generation_span
from miroflow.llm.provider_client_base import LLMProviderClientBase
from miroflow.llm.providers.claude_openrouter_client import ContextLimitError
from miroflow.logging.logger import bootstrap_logger
from miroflow.logging.task_tracer import TaskTracer
from miroflow.tool.manager import ToolManager
from miroflow.utils.io_utils import OutputFormatter, process_input
from miroflow.utils.prompt_utils import (
    generate_agent_specific_system_prompt,
    generate_agent_summarize_prompt,
)
from miroflow.utils.tool_utils import expose_sub_agents_as_tools

logger = bootstrap_logger()


def _list_tools(sub_agent_tool_managers: dict[str, ToolManager]):
    # Use a dictionary to store the cached result
    cache = None

    async def wrapped():
        nonlocal cache
        if cache is None:
            # Only fetch tool definitions if not already cached
            result = {
                name: await tool_manager.get_all_tool_definitions()
                for name, tool_manager in sub_agent_tool_managers.items()
            }
            cache = result
        return cache

    return wrapped


def _generate_message_id() -> str:
    """生成随机message ID，使用LLM常见的格式"""
    # 使用8位随机hex字符串，类似OpenAI API的格式，避免跨对话cache命中
    return f"msg_{uuid.uuid4().hex[:8]}"


class Orchestrator:
    def __init__(
        self,
        main_agent_tool_manager: ToolManager,
        sub_agent_tool_managers: dict[str, ToolManager],
        llm_client: LLMProviderClientBase,
        output_formatter: OutputFormatter,
        cfg: DictConfig,
        task_log: TaskTracer,
    ):
        self.main_agent_tool_manager = main_agent_tool_manager
        self.sub_agent_tool_managers = sub_agent_tool_managers
        self.llm_client = llm_client
        self.output_formatter = output_formatter
        self.cfg = cfg
        self.task_log = task_log
        # call this once, then use cache value
        self._list_sub_agent_tools = _list_tools(sub_agent_tool_managers)

        # 处理add_message_id配置，支持字符串到bool的转换
        add_message_id_val = self.cfg.agent.get("add_message_id", False)
        if isinstance(add_message_id_val, str):
            self.add_message_id: bool = add_message_id_val.lower().strip() == "true"
        else:
            self.add_message_id: bool = bool(add_message_id_val)
        logger.info(
            f"add_message_id配置值: {add_message_id_val} (类型: {type(add_message_id_val)}) -> 解析为: {self.add_message_id}"
        )

        # 将 task_log 传递给 llm_client
        if self.llm_client and task_log:
            self.llm_client.task_log = task_log

    # Could be removed, use task_log.log_step instead, will be removed in the future
    # def _log_step(
    #     self, step_name: str, message: str, status: str = "info", level: str = "info"
    # ):
    #     """记录步骤日志"""
    #     # 使用TaskLog的log_step方法记录到结构化日志中
    #     self.task_log.log_step(step_name, message, status)

    async def _handle_llm_call_with_logging(
        self,
        system_prompt,
        message_history,
        tool_definitions,
        step_id: int,
        purpose: str = "LLM call",
        keep_tool_result: int = -1,
        agent_type: str = "main",
    ) -> tuple[str | None, bool, Any | None]:
        """统一的LLM调用和日志处理
        Returns:
            tuple[Optional[str], bool, Optional[object]]: (response_text, should_break, tool_calls_info)
        """

        # 为user消息添加message ID（如果配置启用且消息还没有ID）
        if self.add_message_id:
            for message in message_history:
                if message.get("role") == "user":
                    content = message.get("content")
                    if isinstance(content, list):
                        # content是列表格式（Anthropic风格）
                        for content_item in content:
                            if content_item.get("type") == "text":
                                text = content_item["text"]
                                # 检查是否已经有message ID
                                if not text.startswith("[msg_"):
                                    message_id = _generate_message_id()
                                    content_item["text"] = f"[{message_id}] {text}"
                    elif isinstance(content, str):
                        # content是字符串格式（简单格式）
                        if not content.startswith("[msg_"):
                            message_id = _generate_message_id()
                            message["content"] = f"[{message_id}] {content}"

        # 保存LLM调用前的消息历史
        if self.task_log:
            if agent_type == "main":
                self.task_log.main_agent_message_history = {
                    "system_prompt": system_prompt,
                    "message_history": message_history,
                }
            elif self.task_log.current_sub_agent_session_id:
                self.task_log.sub_agent_message_history_sessions[
                    self.task_log.current_sub_agent_session_id
                ] = {"system_prompt": system_prompt, "message_history": message_history}
            self.task_log.save()

        try:
            with generation_span(
                input=message_history, model=self.llm_client.model_name
            ) as span:
                response = await self.llm_client.create_message(
                    system_prompt=system_prompt,
                    message_history=message_history,
                    tool_definitions=tool_definitions,
                    keep_tool_result=self.cfg.agent.keep_tool_result,
                    step_id=step_id,
                    task_log=self.task_log,
                    agent_type=agent_type,
                )
                if response and hasattr(response, "choices"):
                    span.span_data.output = [c.dict() for c in response.choices]
                if response and hasattr(response, "usage"):
                    span.span_data.usage = response.usage.dict()

            if response:
                # 使用客户端的响应处理方法
                assistant_response_text, should_break = (
                    self.llm_client.process_llm_response(
                        response, message_history, agent_type
                    )
                )

                # 保存LLM响应处理后的消息历史
                if self.task_log:
                    if agent_type == "main":
                        self.task_log.main_agent_message_history = {
                            "system_prompt": system_prompt,
                            "message_history": message_history,
                        }
                    elif self.task_log.current_sub_agent_session_id:
                        self.task_log.sub_agent_message_history_sessions[
                            self.task_log.current_sub_agent_session_id
                        ] = {
                            "system_prompt": system_prompt,
                            "message_history": message_history,
                        }
                    self.task_log.save()

                # 使用客户端的工具调用信息提取方法
                tool_calls_info = self.llm_client.extract_tool_calls_info(
                    response, assistant_response_text
                )

                if assistant_response_text:
                    self.task_log.log_step(
                        f"{purpose.lower().replace(' ', '_')}_success",
                        f"{purpose} completed successfully",
                    )
                    return assistant_response_text, should_break, tool_calls_info
                else:
                    self.task_log.log_step(
                        f"{purpose.lower().replace(' ', '_')}_failed",
                        f"{purpose} returned no valid response",
                        "failed",
                    )
                    return None, True, None
            else:
                self.task_log.log_step(
                    f"{purpose.lower().replace(' ', '_')}_failed",
                    f"{purpose} returned no valid response",
                    "failed",
                )
                return None, True, None

        except asyncio.TimeoutError:
            logger.debug(f"⚠️ {purpose} 超时了")
            self.task_log.log_step(
                f"{purpose.lower().replace(' ', '_')}_timeout",
                f"{purpose} timed out",
                "failed",
            )
            return None, True, None

        except ContextLimitError as e:
            logger.debug(f"⚠️ {purpose} Context超限: {e}")
            self.task_log.log_step(
                f"{purpose.lower().replace(' ', '_')}_context_limit",
                f"{purpose} context limit exceeded: {str(e)}",
                "warning",
            )
            # 对于context超限，返回特殊标识以便上层处理
            return None, True, "context_limit"

        except Exception as e:
            logger.debug(f"⚠️ {purpose} 调用失败: {e}")
            self.task_log.log_step(
                f"{purpose.lower().replace(' ', '_')}_error",
                f"{purpose} failed: {str(e)}",
                "failed",
            )
            return None, True, None

    async def _handle_summary_with_context_limit_retry(
        self,
        system_prompt,
        message_history,
        tool_definitions,
        purpose,
        task_description,
        task_failed,
        agent_type="main",
        task_guidence="",
    ):
        """
        处理summary时的context超限重试逻辑

        Returns:
            str: final_answer_text - LLM生成的summary文本，失败时为错误信息

        处理的LLM三种情况：
        1. 调用成功：返回生成的summary文本
        2. Context超限或网络问题：移除assistant-user对话重试，标记任务失败
        3. 直到只剩初始system-user消息为止
        """
        retry_count = 0

        while True:
            # 生成summary prompt
            summary_prompt = generate_agent_summarize_prompt(
                task_description + task_guidence,
                task_failed=task_failed,
                agent_type=agent_type,
            )

            # 处理消息历史与summary prompt的合并
            summary_prompt = self.llm_client.handle_max_turns_reached_summary_prompt(
                message_history, summary_prompt
            )

            # 直接添加summary prompt到消息历史
            message_history.append(
                {"role": "user", "content": [{"type": "text", "text": summary_prompt}]}
            )

            response_text, _, tool_calls = await self._handle_llm_call_with_logging(
                system_prompt,
                message_history,
                tool_definitions,
                999,
                purpose,
                agent_type=agent_type,
            )

            if response_text:
                # 调用成功：返回生成的summary文本
                return response_text

            # Context超限或网络问题：尝试移除消息继续重试
            retry_count += 1
            logger.debug(
                f"LLM调用失败，第{retry_count}次重试，移除最近的assistant-user对话"
            )

            # 先移除刚添加的summary prompt
            if message_history and message_history[-1]["role"] == "user":
                message_history.pop()

            # 移除倒数最近的assistant消息（工具调用请求）
            if message_history and message_history[-1]["role"] == "assistant":
                message_history.pop()

            # 一旦需要移除assistant-user对话，任务就失败了（信息被丢弃）
            task_failed = True

            # 如果已经没有更多对话可以移除了
            if len(message_history) <= 2:  # 只剩初始system-user消息
                logger.warning("已移除所有可移除的对话，但仍然无法生成summary")
                break

            self.task_log.log_step(
                f"{agent_type}_summary_context_retry",
                f"Removed assistant-user pair, retry {retry_count}, task marked as failed",
                "warning",
            )

        # 如果移除所有对话后仍然失败
        logger.error("Summary failed after removing all possible messages")
        return "Unable to generate final summary due to persistent network issues. You should try again."

    async def run_sub_agent(
        self, sub_agent_name, task_description, keep_tool_result: int = -1
    ):
        """
        运行子代理
        """
        logger.debug(f"\n=== Starting Sub Agent {sub_agent_name} ===")
        task_description += "\n\nPlease provide the answer and detailed supporting information of the subtask given to you."
        logger.debug(f"Subtask: {task_description}")

        # 开始新的sub-agent session
        self.task_log.start_sub_agent_session(sub_agent_name, task_description)

        # 简化的初始用户内容（无文件附件）
        initial_user_content = [{"type": "text", "text": task_description}]
        message_history = [{"role": "user", "content": initial_user_content}]

        # 获取sub-agent的工具定义
        tool_definitions = await self._list_sub_agent_tools()
        tool_definitions = tool_definitions.get(sub_agent_name, [])
        self.task_log.log_step(
            f"get_sub_{sub_agent_name}_tool_definitions", f"{tool_definitions}"
        )

        if not tool_definitions:
            logger.debug("警告: 未能获取任何工具定义。LLM 可能无法使用工具。")
            self.task_log.log_step(
                f"{sub_agent_name}_no_tools",
                f"No tool definitions available for {sub_agent_name}",
                "warning",
            )

        # 生成sub-agent的系统 Prompt
        system_prompt = self.llm_client.generate_agent_system_prompt(
            date=datetime.datetime.today(),
            mcp_servers=tool_definitions,
        ) + generate_agent_specific_system_prompt(agent_type=sub_agent_name)

        # 限制sub-agent的轮次
        max_turns = self.cfg.agent.sub_agents[sub_agent_name].max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        all_tool_results_content_with_id = []
        task_failed = False  # 跟踪任务是否失败

        while turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- Sub Agent {sub_agent_name} Turn {turn_count} ---")
            self.task_log.save()

            # 使用统一的LLM调用处理
            (
                assistant_response_text,
                should_break,
                tool_calls,
            ) = await self._handle_llm_call_with_logging(
                system_prompt,
                message_history,
                tool_definitions,
                turn_count,
                f"Sub agent {sub_agent_name} turn {turn_count}",
                keep_tool_result=keep_tool_result,
                agent_type=sub_agent_name,
            )

            # 处理LLM响应
            if assistant_response_text:
                if should_break:
                    self.task_log.log_step(
                        "sub_agent_early_termination",
                        f"Sub agent {sub_agent_name} terminated early on turn {turn_count}",
                    )
                    break
            else:
                # LLM调用失败，标记任务失败并结束当前轮次
                if tool_calls == "context_limit":
                    # Context超限情况
                    self.task_log.log_step(
                        "sub_agent_context_limit_reached",
                        f"Sub agent {sub_agent_name} context limit reached, jumping to summary",
                        "warning",
                    )
                else:
                    # 其他LLM调用失败情况
                    self.task_log.log_step(
                        "sub_agent_llm_call_failed",
                        "LLM call failed",
                        "failed",
                    )
                task_failed = True  # 标记任务失败
                break

            # 使用从LLM响应中解析的工具调用
            if tool_calls is None or (
                len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0
            ):
                logger.debug(f"Sub Agent {sub_agent_name} 未要求使用工具，结束任务。")
                self.task_log.log_step(
                    "sub_agent_no_tool_calls",
                    f"No tool calls found in sub agent {sub_agent_name}, ending on turn {turn_count}",
                )
                break

            # 执行工具调用
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # 从配置中获取单轮最大工具调用数
            max_tool_calls = self.cfg.agent.sub_agents[
                sub_agent_name
            ].max_tool_calls_per_turn
            tool_calls_exceeded = len(tool_calls[0]) > max_tool_calls
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Sub agent单轮tool call数量过多({len(tool_calls[0])}个)，只处理前{max_tool_calls}个"
                )

            for call in tool_calls[0][:max_tool_calls]:
                # DEBUG: This place can be used to inject arguments of tools
                server_name = call["server_name"]
                tool_name = call["tool_name"]
                arguments = call["arguments"]
                call_id = call["id"]

                self.task_log.log_step(
                    "sub_agent_tool_call_start",
                    f"Executing {tool_name} on {server_name}",
                )

                call_start_time = time.time()
                try:
                    with function_span(
                        name=f"{server_name}.{tool_name}", input=arguments
                    ) as span:
                        tool_result = await self.sub_agent_tool_managers[
                            sub_agent_name
                        ].execute_tool_call(server_name, tool_name, arguments)
                        span.span_data.output = str(tool_result)

                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    self.task_log.log_step(
                        "sub_agent_tool_call_success",
                        f"Tool {tool_name} executed successfully in {call_duration_ms}ms",
                    )

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )

                except Exception as e:
                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    # Handle empty error messages, especially for TimeoutError
                    error_msg = str(e) or (
                        "Tool execution timeout"
                        if isinstance(e, TimeoutError)
                        else f"Tool execution failed: {type(e).__name__}"
                    )

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "error": error_msg,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )
                    tool_result = {
                        "error": f"Tool call failed: {error_msg}",
                        "server_name": server_name,
                        "tool_name": tool_name,
                    }

                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                logger.debug(f"Tool result: {tool_result}")

                all_tool_results_content_with_id.append((call_id, tool_result_for_llm))

            if len(tool_calls[1]) > 0:
                tool_result = {
                    "result": f"Your tool call format was incorrect, and the tool invocation failed, error_message: {tool_calls[1][0]['error']}; please review it carefully and try calling again.",
                    "server_name": "re-think",
                    "tool_name": "re-think",
                }
                tool_calls_data.append(
                    {
                        "server_name": "",
                        "tool_name": "",
                        "arguments": "",
                        "result": tool_result,
                        "duration_ms": 0,
                        "call_time": datetime.datetime.now(),
                    }
                )
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                all_tool_results_content_with_id.append(("FAILED", tool_result_for_llm))

            message_history = self.llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded
            )

            # 生成summary_prompt来检查token限制
            temp_summary_prompt = generate_agent_summarize_prompt(
                task_description,
                task_failed=True,  # 这里设为True，模拟可能的任务失败情况进行context检查
                agent_type=sub_agent_name,
            )

            # 检查当前context是否会超限，如果超限则自动回退消息并触发summary
            if not self.llm_client.ensure_summary_context(
                message_history, temp_summary_prompt
            ):
                # context预估超限，跳到summary阶段
                task_failed = True  # 标记任务失败
                self.task_log.log_step(
                    f"{sub_agent_name}_context_limit_reached",
                    "Context limit reached, triggering summary",
                    "warning",
                )
                break

        # 继续进行
        logger.debug(
            f"\n=== Sub Agent {sub_agent_name} Completed ({turn_count} turns) ==="
        )

        # 记录浏览代理循环结束
        if turn_count >= max_turns:
            if not task_failed:  # 如果还没有标记为失败，且是因为轮数超限
                task_failed = True
            self.task_log.log_step(
                "sub_agent_max_turns_reached",
                f"Sub agent {sub_agent_name} reached maximum turns ({max_turns})",
                "warning",
            )

        else:
            self.task_log.log_step(
                "sub_agent_loop_completed",
                f"Sub agent {sub_agent_name} loop completed after {turn_count} turns",
            )

        # 最终总结 - 仿照主代理的流程
        self.task_log.log_step(
            "sub_agent_final_summary",
            f"Generating sub agent {sub_agent_name} final summary",
        )

        # 使用context超限重试逻辑生成最终总结
        final_answer_text = await self._handle_summary_with_context_limit_retry(
            system_prompt,
            message_history,
            tool_definitions,
            f"Sub agent {sub_agent_name} final summary",
            task_description,
            task_failed,
            agent_type=sub_agent_name,
        )

        if final_answer_text:
            self.task_log.log_step(
                "sub_agent_final_answer",
                f"Sub agent {sub_agent_name} final answer generated successfully",
            )

        else:
            final_answer_text = (
                f"No final answer generated by sub agent {sub_agent_name}."
            )
            self.task_log.log_step(
                "sub_agent_final_answer",
                f"Failed to generate sub agent {sub_agent_name} final answer",
                "failed",
            )

        logger.debug(f"Sub Agent {sub_agent_name} Final Answer: {final_answer_text}")

        self.task_log.sub_agent_message_history_sessions[
            self.task_log.current_sub_agent_session_id
        ] = {"system_prompt": system_prompt, "message_history": message_history}  # type: ignore
        self.task_log.save()

        self.task_log.end_sub_agent_session(sub_agent_name)
        self.task_log.log_step(
            "sub_agent_completed", f"Sub agent {sub_agent_name} completed", "info"
        )

        # 返回最终答案而不是对话日志，这样主代理可以直接使用
        return final_answer_text

    @retry(wait=wait_exponential(multiplier=15), stop=stop_after_attempt(5))
    async def _o3_extract_hints(self, question: str) -> str:
        """使用O3模型抽取任务提示"""
        client = AsyncOpenAI(api_key=self.cfg.env.openai_api_key, timeout=600)

        instruction = """Carefully analyze the given task description (question) without attempting to solve it directly. Your role is to identify potential challenges and areas that require special attention during the solving process, and provide practical guidance for someone who will solve this task by actively gathering and analyzing information from the web.

Identify and concisely list key points in the question that could potentially impact subsequent information collection or the accuracy and completeness of the problem solution, especially those likely to cause mistakes, carelessness, or confusion during problem-solving.

The question author does not intend to set traps or intentionally create confusion. Interpret the question in the most common, reasonable, and straightforward manner, without speculating about hidden meanings or unlikely scenarios. However, be aware that mistakes, imprecise wording, or inconsistencies may exist due to carelessness or limited subject expertise, rather than intentional ambiguity.

Additionally, when considering potential answers or interpretations, note that question authors typically favor more common and familiar expressions over overly technical, formal, or obscure terminology. They generally prefer straightforward and common-sense interpretations rather than being excessively cautious or academically rigorous in their wording choices.

Also, consider additional flagging issues such as:
- Potential mistakes or oversights introduced unintentionally by the question author due to his misunderstanding, carelessness, or lack of attention to detail.
- Terms or instructions that might have multiple valid interpretations due to ambiguity, imprecision, outdated terminology, or subtle wording nuances.
- Numeric precision, rounding requirements, formatting, or units that might be unclear, erroneous, or inconsistent with standard practices or provided examples.
- Contradictions or inconsistencies between explicit textual instructions and examples or contextual clues provided within the question itself.

Do NOT attempt to guess or infer correct answers, as complete factual information is not yet available. Your responsibility is purely analytical, proactively flagging points that deserve special attention or clarification during subsequent information collection and task solving. Avoid overanalyzing or listing trivial details that would not materially affect the task outcome.

Here is the question:

"""

        # 为O3消息添加message ID（如果配置启用）
        content = instruction + question
        if self.add_message_id:
            message_id = _generate_message_id()
            content = f"[{message_id}] {content}"

        response = await client.chat.completions.create(
            model="o3",
            messages=[{"role": "user", "content": content}],
            reasoning_effort="high",
        )
        result = response.choices[0].message.content

        # 检查结果是否为空，如果为空则抛出异常触发重试
        if not result or not result.strip():
            raise ValueError("O3 hints extraction returned empty result")

        return result

    @retry(wait=wait_exponential(multiplier=15), stop=stop_after_attempt(5))
    async def _get_gaia_answer_type(self, task_description: str) -> str:
        client = AsyncOpenAI(api_key=self.cfg.env.openai_api_key, timeout=600)
        instruction = f"""Input:
`{task_description}`

Question:
Determine the expected data type of the answer. For questions asking to "identify" something, focus on the final answer type, not the identification process. Format requirements in the question often hint at the expected data type. If the question asks you to write a specific word, return string. Choose only one of the four types below:
- number — a pure number (may include decimals or signs), e.g., price, distance, length
- date   — a specific calendar date (e.g., 2025-08-05 or August 5, 2025)
- time   — a specific time of day or formated time cost (e.g., 14:30 or 1:30.12)
- string — any other textual answer

Output:
Return exactly one of the [number, date, time, string], nothing else.
"""
        print(f"Answer type instruction: {instruction}")

        message_id = _generate_message_id()
        response = await client.chat.completions.create(
            model="gpt-4.1",
            messages=[{"role": "user", "content": f"[{message_id}] {instruction}"}],
        )
        answer_type = response.choices[0].message.content
        # 检查结果是否为空，如果为空则抛出异常触发重试
        if not answer_type or not answer_type.strip():
            raise ValueError("answer type returned empty result")

        print(f"Answer type: {answer_type}")

        return answer_type.strip()

    @retry(wait=wait_exponential(multiplier=15), stop=stop_after_attempt(5))
    async def _o3_extract_gaia_final_answer(
        self, answer_type: str, task_description_detail: str, summary: str
    ) -> str:
        """使用O3模型从summary中抽取最终答案"""
        client = AsyncOpenAI(api_key=self.cfg.env.openai_api_key, timeout=600)

        full_prompts = {
            "time": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).  
   – If both are well supported by the summary's evidence, choose the one with stronger or clearer support.  
   – If only one is well supported, use that one.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
   Wrap the answer in `\\boxed{{}}`.

2. **Answer type**
   The boxed content must be a time.

3. **Formatting rules**
   * Follow every formatting instruction in the original question (units, rounding, decimal places, etc.).
   * Do **not** add any units (e.g., "s", "second", "seconds"), unless required.
   * Ensure the correct unit (e.g., hours versus thousand hours); if the question specifies "thousand hours" or "1000 hours", treat it as the required unit — output a number like 13 (thousand hours) instead of 13000 (hours).
   * If the question's written instructions for precision or rounding differ from the examples, treat the examples as authoritative — match their number of decimal places and rounding style.
   
4. **Additional constraints**
   * If the **Agent Summary** is incomplete or unclear, provide the best possible answer (educated guess).

5. **Common pitfalls to avoid**
   * Minor mismatches in the required format.
   * Unit-conversion errors, especially with uncommon units.
   * Incorrect precision, rounding or scale (e.g., 0.01 vs 0.001), **double-check the required level**.
   * Conflicts between textual instructions and example formatting, just follow the example: if the question says to "retain the percentile" but the example shows 0.001, use 0.001 rather than 0.01.
   
---

# Quick reference examples

* If the question says to "rounding the seconds to the nearest hundredth", but the example shows "0.001", 1:23.4567 → 1:23.457
* If the question says to "rounding the seconds to the nearest hundredth", but the example shows "0.001", 10:08.47445 → 10:08.474
* If the question says to "round to one decimal place", but the example shows "0.01", 2:17.456 → 2:17.46
* If the question says to "round to the nearest minute", but the example keeps seconds ("0:45"), 3:44.8 → 3:45
* If the question says "keep three decimal places", but the example shows "0.1", 1:03.987 → 1:03.1
* If the question asks for "thousand hours", 13000 -> 13 

---

# Output

Return the step-by-step process and your final answer wrapped in \\boxed{{...}}, check the **Formatting rules**, **Additional constraints**, **Common pitfalls to avoid** and **Quick reference examples** step by step, and ensure the answer meet the requirements.
""",
            "number": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).  
   – If both are well supported by the summary's evidence, choose the one with stronger or clearer support.  
   – If only one is well supported, use that one.
   – For questions involving calculations, if your answer and the Agent Summary's final answer are numerically similar, prefer the summary's answer.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
   Wrap the answer in `\\boxed{{}}`.

2. **Answer type**
   The boxed content must be a single number.

3. **Formatting rules**
   * Follow every formatting instruction in the original question (units, rounding, decimal places, etc.).
   * Use digits only; do **not** use words, commas or symbols (e.g., "$", "!", "?", "/").
   * Do **not** add any units (e.g., "%", "$", "USD", "Å", "m", "m^2", "m^3"), unless required.
   * Ensure the correct unit (e.g., grams versus kilograms, meters versus kilometers, hours versus thousand hours); if the question specifies "thousand hours" or "1000 hours", treat it as the required unit — output a number like 13 (thousand hours) instead of 13000 (hours).
   
4. **Additional constraints**
   * If the **Agent Summary** is incomplete or unclear, provide the best possible answer (educated guess).

5. **Common pitfalls to avoid**
   * Minor mismatches in the required format.
   * Unit-conversion errors, especially with uncommon units.
   * Incorrect precision, rounding or scale (e.g., 0.01 vs 0.001), **double-check the required level**.
   * Conflicts between textual instructions and example formatting, just follow the example: if the question says to "retain the percentile" but the example shows 0.001, use 0.001 rather than 0.01.
   * Do not partially convert text-based numbers—ensure full and accurate conversion (e.g., "one hundred million" → 100000000, not 100).

---

# Quick reference examples

* $100 → 100
* 100 USD → 100
* €50 → 50
* £75 → 75
* ¥1,000 → 1000
* 1,234 m → 1234
* 3,456,789 kg → 3456789
* 70% → 70
* 12.5% → 12.5
* 0.045 m³ → 0.045
* 0.045 m^3 → 0.045
* −40 °C → -40
* 100 km/h → 100
* 5000 m^2 → 5000
* 2.54 cm → 2.54
* 50 kg → 50
* 4.0 L → 4
* 13 thousand hours → 13
* Page 123/456 → 123/456
* 100 million → 100000000
* 200 Ω → 200
* 200 Å → 200
* 9.81 m/s² → 9.81
* 0 dB → 0

---

# Output

Return the step-by-step process and your final answer wrapped in \\boxed{{...}}, check the **Formatting rules**, **Additional constraints**, **Common pitfalls to avoid** and **Quick reference examples** step by step, and ensure the answer meet the requirements.
""",
            "string": f"""# Inputs

* **Original Question**: `{task_description_detail}`
* **Agent Summary**: `{summary}`

---

# Task

1. **Independently derive** the best possible answer, step by step, based solely on evidence and reasoning from the Agent Summary. **Ignore the summary's "Final Answer" field** at this stage.
2. **Compare** your derived answer to the final answer provided in the Agent Summary (ignoring formatting and phrasing requirements at this stage).  
   – If both are well supported by the summary's evidence, choose the one with stronger or clearer support.  
   – If only one is well supported, use that one.
3. **Revise** your chosen answer to fully satisfy all formatting and phrasing requirements listed below (**Formatting rules**, **Additional constraints**, **Common pitfalls to avoid**, and **Quick reference examples**). These requirements override those in the original question if there is any conflict.

If no answer is clearly supported by the evidence, provide a well-justified educated guess. **Always wrap your final answer in a non-empty \\boxed{{...}}.**

---

# Output Guidelines

1. **Box the answer**
   Wrap the final answer in \\boxed{{...}}.
   
2. **Answer type**
   The boxed content must be **one** of:
   * a single short phrase (fewest words possible)
   * a comma-separated list of numbers and/or strings
   
3. **Formatting rules**
   * Follow every formatting instruction in the original question (alphabetization, sequencing, units, rounding, decimal places, etc.).
   * Omit articles and abbreviations unless explicitly present in the expected answer.
   * If a string contains numeric information, spell out the numbers **unless** the question itself shows them as digits.
   * Do **not** end the answer with ".", "!", "?", or any other punctuation.
   * Use only standard ASCII quotation marks ("" and ''), **not** stylized or curly quotation marks (such as “ ” ‘ ’).
   * Remove invisible or non-printable characters.
   * If the output is lists, apply the rules item-by-item.
   * Avoid unnecessary elaboration - keep the answer as short as possible
     - Do **not** add "count", "number", "count of", "total", or similar quantifying words when the noun itself already refers to the quantity (e.g., use the bare noun form only).
     - No geographical modifiers (e.g., "Western", "Southern"), 
     - Use the simplest, most commonly accepted term for a substance or object (e.g., "diamond" instead of "crystalline diamond", "silicon" instead of "silicon crystals")
   * For mathematical symbols, match the symbol style in the question; never substitute LaTeX commands (e.g., use ≤, not \leq).
   * For birthplaces, give the name as it was at the time of birth, not the current name.

4. **Additional constraints**
   * If the Agent Summary is incomplete or unclear, provide the best possible answer (educated guess).
   * Keep the answer as short and direct as possible—no explanations or parenthetical notes.
   
5. **Common pitfalls to avoid**
   * Minor mismatches between required and produced formats.
   * Conflicts between textual instructions and example formatting—follow the example.
   * **Names**: give only the commonly used first + last name (no middle name unless requested).
   * **Countries**: use the common name (e.g., "China", "Brunei")
   * **Locations**: output only the requested location name, without including time, modifiers (e.g., "The Castle", "The Hotel")
   * When the question provides examples of expected format (e.g., "ripe strawberries" not "strawberries"), follow the exact wording style shown in the examples, preserving all descriptive terms and adjectives as demonstrated.
   * Answer with historically location names when the Agent Summary provides. Never override a historically location name. For example, a birthplace should be referred to by the name it had at the time of birth (i.e., answer the original name).
   * For questions asking to "identify" something, focus on the final answer, not the identification process.

---

# Quick reference examples

* INT. THE CASTLE – DAY 1 → The Castle
* INT. THE HOTEL – NIGHT → The Hotel
* INT. THE SPACESHIP – DAWN → The Spaceship
* INT. THE LIBRARY – EVENING → The Library
* INT. CLASSROOM #3 – MORNING → Classroom #3
* People's Republic of China → China
* citation count → citations
* Brunei Darussalam → Brunei
* United States of America → United States
* Republic of Korea → South Korea
* New York City, USA → New York City
* São Paulo (Brazil) → São Paulo
* John Michael Doe → John Doe
* Mary Anne O'Neil → Mary O'Neil
* Dr. Richard Feynman → Richard Feynman
* INT. ZONE 42 – LEVEL B2 → Zone 42 – Level B2
* INT. THE UNDERWATER BASE – MIDNIGHT → The Underwater Base
* Sam’s Home → Sam's Home
* Mike’s phone → Mike's phone

--- 
# Output
Return the step-by-step process and your final answer wrapped in \\boxed{{...}}, check the **Formatting rules**, **Additional constraints**, **Common pitfalls to avoid** and **Quick reference examples** step by step, and ensure the answer meet the requirements.
""",
        }
        full_prompt = full_prompts.get(
            answer_type if answer_type in ["number", "time"] else "string"
        )

        print("O3 Extract Final Answer Prompt:")
        print(full_prompt)

        message_id = _generate_message_id()
        response = await client.chat.completions.create(
            model="o3",
            messages=[{"role": "user", "content": f"[{message_id}] {full_prompt}"}],
            reasoning_effort="medium",
        )
        result = response.choices[0].message.content

        # 检查结果是否为空，如果为空则抛出异常触发重试
        if not result or not result.strip():
            raise ValueError("O3 final answer extraction returned empty result")

        match = re.search(r"\\boxed{([^}]*)}", result)
        if not match:
            raise ValueError("O3 final answer extraction returned empty answer")

        print("response:", result)

        return result

    async def run_main_agent(
        self, task_description, task_file_name=None, task_id="default_task"
    ):
        """
        Execute the main end-to-end task.
        """
        keep_tool_result = int(self.cfg.agent.keep_tool_result)

        logger.debug(f"\n{'=' * 20} Starting Task: {task_id} {'=' * 20}")
        logger.debug(f"Task Description: {task_description}")
        if task_file_name:
            logger.debug(f"Associated File: {task_file_name}")

        # 1. 处理输入
        initial_user_content, task_description = process_input(
            task_description, task_file_name
        )

        task_guidence = """

Your task is to comprehensively address the question by actively collecting detailed information from the web, and generating a thorough, transparent report. Your goal is NOT to rush a single definitive answer or conclusion, but rather to gather complete information and present ALL plausible candidate answers you find, accompanied by clearly documented supporting evidence, reasoning steps, uncertainties, and explicit intermediate findings.

User does not intend to set traps or create confusion on purpose. Handle the task using the most common, reasonable, and straightforward interpretation, and do not overthink or focus on rare or far-fetched interpretations.

Important considerations:
- Collect comprehensive information from reliable sources to understand all aspects of the question.
- Present every possible candidate answer identified during your information gathering, regardless of uncertainty, ambiguity, or incomplete verification. Avoid premature conclusions or omission of any discovered possibility.
- Explicitly document detailed facts, evidence, and reasoning steps supporting each candidate answer, carefully preserving intermediate analysis results.
- Clearly flag and retain any uncertainties, conflicting interpretations, or alternative understandings identified during information gathering. Do not arbitrarily discard or resolve these issues on your own.
- If the question’s explicit instructions (e.g., numeric precision, formatting, specific requirements) appear inconsistent, unclear, erroneous, or potentially mismatched with general guidelines or provided examples, explicitly record and clearly present all plausible interpretations and corresponding candidate answers.  

Recognize that the original task description might itself contain mistakes, imprecision, inaccuracies, or conflicts introduced unintentionally by the user due to carelessness, misunderstanding, or limited expertise. Do NOT try to second-guess or “correct” these instructions internally; instead, transparently present findings according to every plausible interpretation.

Your objective is maximum completeness, transparency, and detailed documentation to empower the user to judge and select their preferred answer independently. Even if uncertain, explicitly documenting the existence of possible answers significantly enhances the user’s experience, ensuring no plausible solution is irreversibly omitted due to early misunderstanding or premature filtering.
"""

        initial_user_content[0]["text"] = (
            initial_user_content[0]["text"] + task_guidence
        )

        o3_notes = ""  # 初始化o3_notes
        if self.cfg.agent.o3_hint:
            # 执行O3 hints提取
            try:
                o3_hints = await self._o3_extract_hints(task_description)
                o3_notes = (
                    "\n\nBefore you begin, please review the following preliminary notes highlighting subtle or easily misunderstood points in the question, which might help you avoid common pitfalls during your analysis (for reference only; these may not be exhaustive):\n\n"
                    + o3_hints
                )

                # 更新初始用户内容
                original_text = initial_user_content[0]["text"]
                initial_user_content[0]["text"] = original_text + o3_notes
            except Exception as e:
                logger.warning(f"O3 hints extraction failed after retries: {str(e)}")
                o3_notes = ""  # 继续执行，但不使用O3提示

        logger.info("Initial user input content: %s", initial_user_content)
        message_history = [{"role": "user", "content": initial_user_content}]

        # 2. 获取工具定义
        tool_definitions = await self.main_agent_tool_manager.get_all_tool_definitions()
        tool_definitions += expose_sub_agents_as_tools(self.cfg.agent.sub_agents)
        if not tool_definitions:
            logger.debug(
                "Warning: No tool definitions found. LLM cannot use any tools."
            )

        self.task_log.log_step("get_main_tool_definitions", f"{tool_definitions}")

        # 3. 生成系统 Prompt
        system_prompt = self.llm_client.generate_agent_system_prompt(
            date=datetime.datetime.today(),
            mcp_servers=tool_definitions,
        ) + generate_agent_specific_system_prompt(agent_type="main")

        # 4. 主循环：LLM <-> Tools
        max_turns = self.cfg.agent.main_agent.max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        task_failed = False  # 跟踪任务是否失败
        while turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- Main Agent Turn {turn_count} ---")
            self.task_log.save()

            # 使用统一的LLM调用处理
            (
                assistant_response_text,
                should_break,
                tool_calls,
            ) = await self._handle_llm_call_with_logging(
                system_prompt,
                message_history,
                tool_definitions,
                turn_count,
                f"Main agent turn {turn_count}",
                keep_tool_result=keep_tool_result,
                agent_type="main",
            )

            # 处理LLM响应
            if assistant_response_text:
                if should_break:
                    break
            else:
                # LLM调用失败，标记任务失败并结束当前轮次
                if tool_calls == "context_limit":
                    # Context超限情况
                    self.task_log.log_step(
                        "main_agent_context_limit_reached",
                        "Main agent context limit reached, jumping to summary",
                        "warning",
                    )
                else:
                    # 其他LLM调用失败情况
                    self.task_log.log_step(
                        step_name="main_agent",
                        message="LLM call failed",
                        status="failed",
                    )
                task_failed = True  # 标记任务失败
                break

            if tool_calls is None or (
                len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0
            ):
                # 没有工具调用，认为是最终答案
                logger.debug("LLM 未要求使用工具，流程结束。")
                break  # 退出循环

            # 7. 执行工具调用 (按顺序执行)
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # 从配置中获取单轮最大工具调用数
            max_tool_calls = self.cfg.agent.main_agent.max_tool_calls_per_turn
            tool_calls_exceeded = len(tool_calls[0]) > max_tool_calls
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] 单轮tool call数量过多({len(tool_calls[0])}个)，只处理前{max_tool_calls}个"
                )

            for call in tool_calls[0][:max_tool_calls]:
                server_name = call["server_name"]
                tool_name = call["tool_name"]
                arguments = call["arguments"]
                call_id = call["id"]

                call_start_time = time.time()
                try:
                    if server_name.startswith("agent-"):
                        with function_span(
                            name=f"{server_name}.{tool_name}", input=arguments
                        ) as span:
                            sub_agent_result = await self.run_sub_agent(
                                server_name, arguments["subtask"], keep_tool_result
                            )
                            tool_result = {
                                "server_name": server_name,
                                "tool_name": tool_name,
                                "result": sub_agent_result,
                            }
                            span.span_data.output = str(tool_result)
                    else:
                        with function_span(
                            name=f"{server_name}.{tool_name}", input=arguments
                        ) as span:
                            tool_result = (
                                await self.main_agent_tool_manager.execute_tool_call(
                                    server_name=server_name,
                                    tool_name=tool_name,
                                    arguments=arguments,
                                )
                            )
                            span.span_data.output = str(tool_result)

                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "result": tool_result,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )

                except Exception as e:
                    call_end_time = time.time()
                    call_duration_ms = int((call_end_time - call_start_time) * 1000)

                    # Handle empty error messages, especially for TimeoutError
                    error_msg = str(e) or (
                        "Tool execution timeout"
                        if isinstance(e, TimeoutError)
                        else f"Tool execution failed: {type(e).__name__}"
                    )

                    tool_calls_data.append(
                        {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "arguments": arguments,
                            "error": error_msg,
                            "duration_ms": call_duration_ms,
                            "call_time": datetime.datetime.now(),
                        }
                    )
                    tool_result = {
                        "server_name": server_name,
                        "tool_name": tool_name,
                        "error": error_msg,
                    }

                # 格式化结果以反馈给 LLM (更简洁)
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                # all_tool_results_content.extend(tool_result_for_llm)  # 收集所有工具结果
                all_tool_results_content_with_id.append((call_id, tool_result_for_llm))

            if len(tool_calls[1]) > 0:
                tool_result = {
                    "result": f"Your tool call format was incorrect, and the tool invocation failed, error_message: {tool_calls[1][0]['error']}; please review it carefully and try calling again.",
                    "server_name": "re-think",
                    "tool_name": "re-think",
                }
                tool_calls_data.append(
                    {
                        "server_name": "",
                        "tool_name": "",
                        "arguments": "",
                        "result": tool_result,
                        "duration_ms": 0,
                        "call_time": datetime.datetime.now(),
                    }
                )
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                all_tool_results_content_with_id.append(("FAILED", tool_result_for_llm))

            # Update message history with tool calls data (llm client specific)
            message_history = self.llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded
            )

            # 生成summary_prompt来检查token限制
            temp_summary_prompt = generate_agent_summarize_prompt(
                task_description + task_guidence,
                task_failed=True,  # 这里设为True，模拟可能的任务失败情况进行context检查
                agent_type="main",
            )

            # 检查当前context是否会超限，如果超限则自动回退消息并触发summary
            if not self.llm_client.ensure_summary_context(
                message_history, temp_summary_prompt
            ):
                # context超限，跳到summary阶段
                task_failed = True  # 标记任务失败
                self.task_log.log_step(
                    "main_context_limit_reached",
                    "Context limit reached, triggering summary",
                    "warning",
                )
                break

        # 记录主循环结束
        if turn_count >= max_turns:
            if not task_failed:  # 如果还没有标记为失败，且是因为轮数超限
                task_failed = True
            self.task_log.log_step(
                "max_turns_reached",
                f"Reached maximum turns ({max_turns})",
                "warning",
            )

        else:
            self.task_log.log_step(
                "main_loop_completed", f"Main loop completed after {turn_count} turns"
            )

        # 最终总结
        self.task_log.log_step("final_summary", "Generating final summary")

        # 使用context超限重试逻辑生成最终总结
        final_answer_text = await self._handle_summary_with_context_limit_retry(
            system_prompt,
            message_history,
            tool_definitions,
            "Final summary generation",
            task_description,
            task_failed,
            agent_type="main",
            task_guidence=task_guidence,
        )

        # 处理响应结果
        if final_answer_text:
            self.task_log.log_step(
                "final_answer", "Final answer extracted successfully"
            )

            # Log the final answer
            self.task_log.log_step(
                "final_answer_content", f"Final answer content: {final_answer_text}"
            )

            # 使用O3模型抽取最终答案
            if self.cfg.agent.o3_final_answer:
                # 执行O3最终答案提取
                try:
                    answer_type = await self._get_gaia_answer_type(task_description)

                    o3_extracted_answer = await self._o3_extract_gaia_final_answer(
                        answer_type,
                        task_description,
                        final_answer_text,
                    )

                    # 将O3抽取的答案伪装成assistant返回的结果添加到消息历史
                    assistant_o3_message = {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "text",
                                "text": f"O3 extracted final answer:\n{o3_extracted_answer}",
                            }
                        ],
                    }
                    message_history.append(assistant_o3_message)

                    # 拼接original summary和o3答案作为最终结果
                    final_answer_text = f"{final_answer_text}\n\nO3 Extracted Answer:\n{o3_extracted_answer}"

                except Exception as e:
                    logger.warning(
                        f"O3 final answer extraction failed after retries: {str(e)}"
                    )
                    # 继续使用原始的 final_answer_text

        else:
            final_answer_text = "No final answer generated."
            self.task_log.log_step(
                "final_answer", "Failed to extract final answer", "failed"
            )

        logger.debug(f"LLM Final Answer: {final_answer_text}")

        # 保存最终的消息历史（包含O3处理结果）
        self.task_log.main_agent_message_history = {
            "system_prompt": system_prompt,
            "message_history": message_history,
        }
        self.task_log.save()

        # 格式化并返回最终输出
        self.task_log.log_step("format_output", "Formatting final output")
        final_summary, final_boxed_answer, usage_log = (
            self.output_formatter.format_final_summary_and_log(
                final_answer_text, self.llm_client
            )
        )

        self.task_log.log_step("usage_calculation", f"Usage log: {usage_log}")

        logger.debug(f"\n{'=' * 20} Task {task_id} Finished {'=' * 20}")
        self.task_log.log_step(
            "task_completed", f"Main agent task {task_id} completed successfully"
        )

        return final_summary, final_boxed_answer
