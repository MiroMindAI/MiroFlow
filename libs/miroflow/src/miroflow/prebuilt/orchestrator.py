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
    """Generate random message ID using common LLM format"""
    # Use 8-character random hex string, similar to OpenAI API format, avoid cross-conversation cache hits
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

        # Handle add_message_id configuration, support string to bool conversion
        add_message_id_val = self.cfg.agent.get("add_message_id", False)
        if isinstance(add_message_id_val, str):
            self.add_message_id: bool = add_message_id_val.lower().strip() == "true"
        else:
            self.add_message_id: bool = bool(add_message_id_val)
        logger.info(
            f"add_message_id config value: {add_message_id_val} (type: {type(add_message_id_val)}) -> parsed as: {self.add_message_id}"
        )

        # Pass task_log to llm_client
        if self.llm_client and task_log:
            self.llm_client.task_log = task_log

    # Could be removed, use task_log.log_step instead, will be removed in the future
    # def _log_step(
    #     self, step_name: str, message: str, status: str = "info", level: str = "info"
    # ):
    #     """Log step information"""
    #     # Use TaskLog's log_step method to record to structured log
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
        """Unified LLM call and logging handling
        Returns:
            tuple[Optional[str], bool, Optional[object]]: (response_text, should_break, tool_calls_info)
        """

        # Add message ID to user messages (if configured and message doesn't have ID yet)
        if self.add_message_id:
            for message in message_history:
                if message.get("role") == "user":
                    content = message.get("content")
                    if isinstance(content, list):
                        # content is list format (Anthropic style)
                        for content_item in content:
                            if content_item.get("type") == "text":
                                text = content_item["text"]
                                # Check if message ID already exists
                                if not text.startswith("[msg_"):
                                    message_id = _generate_message_id()
                                    content_item["text"] = f"[{message_id}] {text}"
                    elif isinstance(content, str):
                        # content is string format (simple format)
                        if not content.startswith("[msg_"):
                            message_id = _generate_message_id()
                            message["content"] = f"[{message_id}] {content}"

        # Save message history before LLM call
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
                # Use client's response processing method
                assistant_response_text, should_break = (
                    self.llm_client.process_llm_response(
                        response, message_history, agent_type
                    )
                )

                # Save message history after LLM response processing
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

                # Use client's tool call information extraction method
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
            logger.debug(f"⚠️ {purpose} timed out")
            self.task_log.log_step(
                f"{purpose.lower().replace(' ', '_')}_timeout",
                f"{purpose} timed out",
                "failed",
            )
            return None, True, None

        except ContextLimitError as e:
            logger.debug(f"⚠️ {purpose} context limit exceeded: {e}")
            self.task_log.log_step(
                f"{purpose.lower().replace(' ', '_')}_context_limit",
                f"{purpose} context limit exceeded: {str(e)}",
                "warning",
            )
            # For context limit exceeded, return special identifier for upper layer handling
            return None, True, "context_limit"

        except Exception as e:
            logger.debug(f"⚠️ {purpose} call failed: {e}")
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
        Handle context limit retry logic when processing summary

        Returns:
            str: final_answer_text - LLM generated summary text, error message on failure

        Handle three LLM scenarios:
        1. Call successful: return generated summary text
        2. Context limit exceeded or network issues: remove assistant-user dialogue and retry, mark task as failed
        3. Until only initial system-user messages remain
        """
        retry_count = 0

        while True:
            # Generate summary prompt
            summary_prompt = generate_agent_summarize_prompt(
                task_description + task_guidence,
                task_failed=task_failed,
                agent_type=agent_type,
            )

            # Handle merging of message history and summary prompt
            summary_prompt = self.llm_client.handle_max_turns_reached_summary_prompt(
                message_history, summary_prompt
            )

            # Directly add summary prompt to message history
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
                # Call successful: return generated summary text
                return response_text

            # Context limit exceeded or network issues: try removing messages and retry
            retry_count += 1
            logger.debug(
                f"LLM call failed, attempt {retry_count} retry, removing recent assistant-user dialogue"
            )

            # First remove the just-added summary prompt
            if message_history and message_history[-1]["role"] == "user":
                message_history.pop()

            # Remove the most recent assistant message (tool call request)
            if message_history and message_history[-1]["role"] == "assistant":
                message_history.pop()

            # Once assistant-user dialogue needs to be removed, task fails (information is lost)
            task_failed = True

            # If there are no more dialogues to remove
            if len(message_history) <= 2:  # Only initial system-user messages remain
                logger.warning(
                    "Removed all removable dialogues, but still unable to generate summary"
                )
                break

            self.task_log.log_step(
                f"{agent_type}_summary_context_retry",
                f"Removed assistant-user pair, retry {retry_count}, task marked as failed",
                "warning",
            )

        # If still fails after removing all dialogues
        logger.error("Summary failed after removing all possible messages")
        return "Unable to generate final summary due to persistent network issues. You should try again."

    async def run_sub_agent(
        self, sub_agent_name, task_description, keep_tool_result: int = -1
    ):
        """
        Run sub agent
        """
        logger.debug(f"\n=== Starting Sub Agent {sub_agent_name} ===")
        task_description += "\n\nPlease provide the answer and detailed supporting information of the subtask given to you."
        logger.debug(f"Subtask: {task_description}")

        # Start new sub-agent session
        self.task_log.start_sub_agent_session(sub_agent_name, task_description)

        # Simplified initial user content (no file attachments)
        initial_user_content = [{"type": "text", "text": task_description}]
        message_history = [{"role": "user", "content": initial_user_content}]

        # Get sub-agent tool definitions
        tool_definitions = await self._list_sub_agent_tools()
        tool_definitions = tool_definitions.get(sub_agent_name, [])
        self.task_log.log_step(
            f"get_sub_{sub_agent_name}_tool_definitions", f"{tool_definitions}"
        )

        if not tool_definitions:
            logger.debug(
                "Warning: Failed to get any tool definitions. LLM may not be able to use tools."
            )
            self.task_log.log_step(
                f"{sub_agent_name}_no_tools",
                f"No tool definitions available for {sub_agent_name}",
                "warning",
            )

        # Generate sub-agent system prompt
        system_prompt = self.llm_client.generate_agent_system_prompt(
            date=datetime.datetime.today(),
            mcp_servers=tool_definitions,
        ) + generate_agent_specific_system_prompt(agent_type=sub_agent_name)

        # Limit sub-agent turns
        max_turns = self.cfg.agent.sub_agents[sub_agent_name].max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        all_tool_results_content_with_id = []
        task_failed = False  # Track whether task failed

        while turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- Sub Agent {sub_agent_name} Turn {turn_count} ---")
            self.task_log.save()

            # Use unified LLM call handling
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

            # Handle LLM response
            if assistant_response_text:
                if should_break:
                    self.task_log.log_step(
                        "sub_agent_early_termination",
                        f"Sub agent {sub_agent_name} terminated early on turn {turn_count}",
                    )
                    break
            else:
                # LLM call failed, mark task as failed and end current turn
                if tool_calls == "context_limit":
                    # Context limit exceeded situation
                    self.task_log.log_step(
                        "sub_agent_context_limit_reached",
                        f"Sub agent {sub_agent_name} context limit reached, jumping to summary",
                        "warning",
                    )
                else:
                    # Other LLM call failure situations
                    self.task_log.log_step(
                        "sub_agent_llm_call_failed",
                        "LLM call failed",
                        "failed",
                    )
                task_failed = True  # Mark task as failed
                break

            # Use tool calls parsed from LLM response
            if tool_calls is None or (
                len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0
            ):
                logger.debug(
                    f"Sub Agent {sub_agent_name} did not request tool use, ending task."
                )
                self.task_log.log_step(
                    "sub_agent_no_tool_calls",
                    f"No tool calls found in sub agent {sub_agent_name}, ending on turn {turn_count}",
                )
                break

            # Execute tool calls
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # Get maximum tool calls per turn from configuration
            max_tool_calls = self.cfg.agent.sub_agents[
                sub_agent_name
            ].max_tool_calls_per_turn
            tool_calls_exceeded = len(tool_calls[0]) > max_tool_calls
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Sub agent single turn tool call count too high ({len(tool_calls[0])} calls), only processing first {max_tool_calls}"
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

            # Generate summary_prompt to check token limit
            temp_summary_prompt = generate_agent_summarize_prompt(
                task_description,
                task_failed=True,  # Set to True here to simulate potential task failure for context checking
                agent_type=sub_agent_name,
            )

            # Check if current context would exceed limit, auto rollback messages and trigger summary if exceeded
            if not self.llm_client.ensure_summary_context(
                message_history, temp_summary_prompt
            ):
                # Context estimated to exceed limit, jump to summary stage
                task_failed = True  # Mark task as failed
                self.task_log.log_step(
                    f"{sub_agent_name}_context_limit_reached",
                    "Context limit reached, triggering summary",
                    "warning",
                )
                break

        # Continue execution
        logger.debug(
            f"\n=== Sub Agent {sub_agent_name} Completed ({turn_count} turns) ==="
        )

        # Record browser agent loop end
        if turn_count >= max_turns:
            if (
                not task_failed
            ):  # If not yet marked as failed and due to turn limit exceeded
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

        # Final summary - following main agent process
        self.task_log.log_step(
            "sub_agent_final_summary",
            f"Generating sub agent {sub_agent_name} final summary",
        )

        # Use context limit retry logic to generate final summary
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

        # Return final answer instead of dialogue log, so main agent can use directly
        return final_answer_text

    @retry(wait=wait_exponential(multiplier=15), stop=stop_after_attempt(5))
    async def _o3_extract_hints(self, question: str) -> str:
        """Use O3 model to extract task hints"""
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

        # Add message ID for O3 messages (if configured)
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

        # Check if result is empty, raise exception to trigger retry if empty
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
        # Check if result is empty, raise exception to trigger retry if empty
        if not answer_type or not answer_type.strip():
            raise ValueError("answer type returned empty result")

        print(f"Answer type: {answer_type}")

        return answer_type.strip()

    @retry(wait=wait_exponential(multiplier=15), stop=stop_after_attempt(5))
    async def _o3_extract_gaia_final_answer(
        self, answer_type: str, task_description_detail: str, summary: str
    ) -> str:
        """Use O3 model to extract final answer from summary"""
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

        # Check if result is empty, raise exception to trigger retry if empty
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

        # 1. Process input
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

        o3_notes = ""  # Initialize o3_notes
        if self.cfg.agent.o3_hint:
            # Execute O3 hints extraction
            try:
                o3_hints = await self._o3_extract_hints(task_description)
                o3_notes = (
                    "\n\nBefore you begin, please review the following preliminary notes highlighting subtle or easily misunderstood points in the question, which might help you avoid common pitfalls during your analysis (for reference only; these may not be exhaustive):\n\n"
                    + o3_hints
                )

                # Update initial user content
                original_text = initial_user_content[0]["text"]
                initial_user_content[0]["text"] = original_text + o3_notes
            except Exception as e:
                logger.warning(f"O3 hints extraction failed after retries: {str(e)}")
                o3_notes = ""  # Continue execution but without O3 hints

        logger.info("Initial user input content: %s", initial_user_content)
        message_history = [{"role": "user", "content": initial_user_content}]

        # 2. Get tool definitions
        tool_definitions = await self.main_agent_tool_manager.get_all_tool_definitions()
        tool_definitions += expose_sub_agents_as_tools(self.cfg.agent.sub_agents)
        if not tool_definitions:
            logger.debug(
                "Warning: No tool definitions found. LLM cannot use any tools."
            )

        self.task_log.log_step("get_main_tool_definitions", f"{tool_definitions}")

        # 3. Generate system prompt
        system_prompt = self.llm_client.generate_agent_system_prompt(
            date=datetime.datetime.today(),
            mcp_servers=tool_definitions,
        ) + generate_agent_specific_system_prompt(agent_type="main")

        # 4. Main loop: LLM <-> Tools
        max_turns = self.cfg.agent.main_agent.max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        task_failed = False  # Track whether task failed
        while turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- Main Agent Turn {turn_count} ---")
            self.task_log.save()

            # Use unified LLM call handling
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

            # Handle LLM response
            if assistant_response_text:
                if should_break:
                    break
            else:
                # LLM call failed, mark task as failed and end current turn
                if tool_calls == "context_limit":
                    # Context limit exceeded situation
                    self.task_log.log_step(
                        "main_agent_context_limit_reached",
                        "Main agent context limit reached, jumping to summary",
                        "warning",
                    )
                else:
                    # Other LLM call failure situations
                    self.task_log.log_step(
                        step_name="main_agent",
                        message="LLM call failed",
                        status="failed",
                    )
                task_failed = True  # Mark task as failed
                break

            if tool_calls is None or (
                len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0
            ):
                # No tool calls, consider as final answer
                logger.debug("LLM did not request tool use, process ends.")
                break  # Exit loop

            # 7. Execute tool calls (in sequence)
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # Get maximum tool calls per turn from configuration
            max_tool_calls = self.cfg.agent.main_agent.max_tool_calls_per_turn
            tool_calls_exceeded = len(tool_calls[0]) > max_tool_calls
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Single turn tool call count too high ({len(tool_calls[0])} calls), only processing first {max_tool_calls}"
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

                # Format result for LLM feedback (more concise)
                tool_result_for_llm = self.output_formatter.format_tool_result_for_user(
                    tool_result
                )
                # all_tool_results_content.extend(tool_result_for_llm)  # Collect all tool results
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

            # Generate summary_prompt to check token limit
            temp_summary_prompt = generate_agent_summarize_prompt(
                task_description + task_guidence,
                task_failed=True,  # Set to True here to simulate possible task failure for context checking
                agent_type="main",
            )

            # Check if current context would exceed limit, auto rollback messages and trigger summary if exceeded
            if not self.llm_client.ensure_summary_context(
                message_history, temp_summary_prompt
            ):
                # Context limit exceeded, jump to summary stage
                task_failed = True  # Mark task as failed
                self.task_log.log_step(
                    "main_context_limit_reached",
                    "Context limit reached, triggering summary",
                    "warning",
                )
                break

        # Record main loop end
        if turn_count >= max_turns:
            if (
                not task_failed
            ):  # If not yet marked as failed and due to turn limit exceeded
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

        # Final summary
        self.task_log.log_step("final_summary", "Generating final summary")

        # Use context limit retry logic to generate final summary
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

        # Handle response result
        if final_answer_text:
            self.task_log.log_step(
                "final_answer", "Final answer extracted successfully"
            )

            # Log the final answer
            self.task_log.log_step(
                "final_answer_content", f"Final answer content: {final_answer_text}"
            )

            # Use O3 model to extract final answer
            if self.cfg.agent.o3_final_answer:
                # Execute O3 final answer extraction
                try:
                    answer_type = await self._get_gaia_answer_type(task_description)

                    o3_extracted_answer = await self._o3_extract_gaia_final_answer(
                        answer_type,
                        task_description,
                        final_answer_text,
                    )

                    # Disguise O3 extracted answer as assistant returned result and add to message history
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

                    # Concatenate original summary and o3 answer as final result
                    final_answer_text = f"{final_answer_text}\n\nO3 Extracted Answer:\n{o3_extracted_answer}"

                except Exception as e:
                    logger.warning(
                        f"O3 final answer extraction failed after retries: {str(e)}"
                    )
                    # Continue using original final_answer_text

        else:
            final_answer_text = "No final answer generated."
            self.task_log.log_step(
                "final_answer", "Failed to extract final answer", "failed"
            )

        logger.debug(f"LLM Final Answer: {final_answer_text}")

        # Save final message history (including O3 processing results)
        self.task_log.main_agent_message_history = {
            "system_prompt": system_prompt,
            "message_history": message_history,
        }
        self.task_log.save()

        # Format and return final output
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
