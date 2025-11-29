# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import datetime
import json
import os
import re
import sys
import time
import uuid
from typing import Any, Callable, Dict, List, Literal, Optional
import importlib
from config.agent_prompts.base_agent_prompt import BaseAgentPrompt

from omegaconf import DictConfig


from src.llm.provider_client_base import LLMProviderClientBase
from src.llm.providers.claude_openrouter_client import ContextLimitError
from src.logging.logger import bootstrap_logger
from src.logging.task_tracer import TaskTracer
from src.tool.manager import ToolManager
from src.utils.io_utils import OutputFormatter, process_input
from src.utils.tool_utils import expose_sub_agents_as_tools
from src.utils.summary_utils import (
    extract_hints,
    extract_gaia_final_answer,
    extract_browsecomp_zh_final_answer,
)
from src.utils.stream_parsing_utils import TextInterceptor
from src.utils.history_input import make_muti_turn_prompt

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)

SCRAPE_MAX_LENGTH = 20000
try:
    SCRAPE_MAX_LENGTH = int(os.getenv("SCRAPE_MAX_LENGTH", "20000"))
except:
    pass


def _list_tools(sub_agent_tool_managers: dict[str, ToolManager]):
    # Use a dictionary to store the cached result
    cache = None

    async def wrapped():
        nonlocal cache
        if cache is None:
            # Only fetch tool definitions if not already cached
            # Handle empty sub_agent_tool_managers (single agent mode)
            if not sub_agent_tool_managers:
                result = {}
            else:
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


def _load_agent_prompt_class(prompt_class_name: str) -> BaseAgentPrompt:
    # Dynamically import the class from the config.agent_prompts module
    if not isinstance(prompt_class_name, str) or not prompt_class_name.isidentifier():
        raise ValueError(f"Invalid prompt class name: {prompt_class_name}")

    try:
        # Import the module dynamically
        agent_prompts_module = importlib.import_module("config.agent_prompts")
        # Get the class from the module
        PromptClass = getattr(agent_prompts_module, prompt_class_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(
            f"Could not import class '{prompt_class_name}' from 'config.agent_prompts': {e}"
        )
    return PromptClass()

AgentName = Literal["main", "reporter", "browsing"]
class Orchestrator:
    def __init__(
        self,
        main_agent_tool_manager: ToolManager,
        sub_agent_tool_managers: dict[str, ToolManager],
        llm_client: LLMProviderClientBase,
        output_formatter: OutputFormatter,
        cfg: DictConfig,
        task_log: TaskTracer,
        sub_agent_llm_client: Optional[LLMProviderClientBase] = None,
        stream_queue: Optional[Any] = None,
        tool_definitions: Optional[List[Dict[str, Any]]] = None,
        sub_agent_tool_definitions: Optional[Dict[str, List[Dict[str, Any]]]] = None,
        debug_config: Optional[dict] = None,
    ):
        if debug_config:
            self.debug_config = debug_config
        else:
            self.debug_config = {}
        self.main_agent_tool_manager = main_agent_tool_manager
        self.sub_agent_tool_managers = sub_agent_tool_managers
        self.llm_client = llm_client
        self.sub_agent_llm_client = (
            sub_agent_llm_client or llm_client
        )  # Use client from main agent if not provided
        self.output_formatter = output_formatter
        self.cfg = cfg
        self.task_log = task_log
        self.stream_queue = stream_queue
        self.key_message_interceptor = TextInterceptor(["<use_mcp_tool>"])
        self.tool_definitions = tool_definitions
        self.sub_agent_tool_definitions = sub_agent_tool_definitions
        # call this once, then use cache value
        self._list_sub_agent_tools = _list_tools(sub_agent_tool_managers)

        self.chinese_context = (
            self.cfg.main_agent.chinese_context.lower().strip() == "true"
        )

        # Handle add_message_id configuration, support string to bool conversion
        add_message_id_val = self.cfg.main_agent.get("add_message_id", False)
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
        if (
            self.sub_agent_llm_client
            and task_log
            and self.sub_agent_llm_client != self.llm_client
        ):
            self.sub_agent_llm_client.task_log = task_log

    async def _stream_update(self, event_type: str, data: dict):
        """Send streaming update in new SSE protocol format"""
        if self.stream_queue:
            try:
                stream_message = {
                    "event": event_type,
                    "data": data,
                }
                await self.stream_queue.put(stream_message)
            except Exception as e:
                logger.warning(f"Failed to send stream update: {e}")
    
    async def _stream_start_workflow(self,  user_input: str, workflow_id: str = None) -> str:
        """Send start_of_workflow event"""
        if not workflow_id:
            workflow_id = str(uuid.uuid4())
        await self._stream_update("start_of_workflow", {
            "workflow_id": workflow_id,
            "input": [
                {
                    "role": "user",
                    "content": user_input,
                }
            ]
        })
        return workflow_id
    
    async def _stream_end_workflow(self, workflow_id: str):
        """Send end_of_workflow event"""
        await self._stream_update("end_of_workflow", {
            "workflow_id": workflow_id,
        })
        if self.stream_queue:
            try:
                await self.stream_queue.put(None)
            except Exception as e:
                logger.warning(f"Failed to send end_of_workflow: {e}")
        
    async def _stream_show_error(self, error: str):
        """Send show_error event"""
        await self._stream_tool_call("show_error", {"error": error})
        if self.stream_queue:
            try:
                await self.stream_queue.put(None)
            except Exception as e:
                logger.warning(f"Failed to send show_error: {e}")
    
    async def _stream_start_agent(self, agent_name: AgentName, display_name: str = None):
        """Send start_of_agent event"""
        agent_id = str(uuid.uuid4())
        await self._stream_update("start_of_agent", {
            "agent_name": agent_name,
            "display_name": display_name,
            "agent_id": agent_id,
        })
        return agent_id
    
    async def _stream_end_agent(self, agent_name: AgentName, agent_id: str):
        """Send end_of_agent event"""
        await self._stream_update("end_of_agent", {
            "agent_name": agent_name,
            "agent_id": agent_id,
        })
    
    async def _stream_start_llm(self, agent_name: AgentName, display_name: str = None):
        """Send start_of_llm event"""
        await self._stream_update("start_of_llm", {
            "agent_name": agent_name,
            "display_name": display_name,
        })
    
    async def _stream_end_llm(self, agent_name: AgentName):
        """Send end_of_llm event"""
        await self._stream_update("end_of_llm", {
            "agent_name": agent_name,
        })
    
    async def _stream_message(self, message_id: str, delta_content: str):
        """Send message event"""
        await self._stream_update("message", {
            "message_id": message_id,
            "delta": {
                "content": delta_content,
            },
        })

    async def _stream_tool_call(self, tool_name: str, payload: dict, streaming: bool = False, tool_call_id: str = None) -> str:
        """Send tool_call event"""
        if not tool_call_id:
            tool_call_id = str(uuid.uuid4())
        
        if streaming:
            for key, value in payload.items():
                await self._stream_update("tool_call", {
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "delta_input": {
                        key: value
                    },
                })
        else:
            # Send complete tool call
            await self._stream_update("tool_call", {
                "tool_call_id": tool_call_id,
                "tool_name": tool_name,
                "tool_input": payload,
            })
        
        return tool_call_id

    async def _stream_usage_info(self, agent_name: AgentName, usage_data: Dict[str, Any], scene: str):
        """
        Send usage_info event
        
        :param agent_name: Name of the agent
        :param usage_data: Usage data dictionary
        :param scene: Scene identifier - "tool_call", "main_agent_end", or "sub_agent_end"
        """
        await self._stream_update("usage_info", {
            "agent_name": agent_name,
            "scene": scene,
            "usage": usage_data,
        })

    async def _intercept_key_message(self, message_id: str, message: str, is_last: bool):
        """拦截关键字，如果关键字在消息中，则不发送，返回False，否则发送，返回True"""
        # logger.info(f"✅收到消息：{message}, 是否是最后一个：{is_last}")
        result = self.key_message_interceptor.process(message, is_last)
        if result is not None:
            if self.key_message_interceptor.is_unbreakable_string(result):
                return False
            else:
                await self._stream_tool_call("show_text", {"text": result}, True, message_id)
                await asyncio.sleep(0)
                return True
        return True
    
    async def _streaming_final_message(self, message_id: str, message: str, is_last: bool):
        """拦截关键字，如果关键字在消息中，则不发送，返回False，否则发送，返回True"""
        result = self.key_message_interceptor.process(message, is_last)
        if result is not None:
            if self.key_message_interceptor.is_unbreakable_string(result):
                return False
            else:
                await self._stream_message(message_id=message_id, delta_content=result)
                await asyncio.sleep(0)
                return True
        return True

    def get_scrape_result(self, result: str) -> str:
        """
        Check if the scrape result is an error
        """
        try:
            scrape_result_dict = json.loads(result)
            text = scrape_result_dict.get("text")
            if text and len(text) > SCRAPE_MAX_LENGTH:
                text = text[:SCRAPE_MAX_LENGTH]
            return json.dumps({"text": text},ensure_ascii=False)
        except json.JSONDecodeError:
            if isinstance(result, str) and len(result) > SCRAPE_MAX_LENGTH:
                result = result[:SCRAPE_MAX_LENGTH]
            return result

    def post_process_tool_call_result(self, tool_name, tool_call_result: dict):
        """处理工具调用结果"""
        if "result" in tool_call_result and tool_name == "scrape":
            tool_call_result['result'] = self.get_scrape_result( tool_call_result['result'])
        return tool_call_result


    async def _handle_llm_call_with_logging(
        self,
        system_prompt,
        message_history,
        tool_definitions,
        step_id: int,
        purpose: str = "LLM call",
        keep_tool_result: int = -1,
        agent_type: str = "main",
        stream_message_callback: Callable = None    
    ) -> tuple[str | None, bool, Any | None]:
        """Unified LLM call and logging handling
        Returns:
            tuple[Optional[str], bool, Optional[object]]: (response_text, should_break, tool_calls_info)
        """

        # Select correct LLM client based on agent_type
        current_llm_client = (
            self.llm_client if agent_type == "main" else self.sub_agent_llm_client
        )

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
            response = await current_llm_client.create_message(
                system_prompt=system_prompt,
                message_history=message_history,
                tool_definitions=tool_definitions,
                keep_tool_result=self.cfg.main_agent.keep_tool_result,
                step_id=step_id,
                task_log=self.task_log,
                agent_type=agent_type,
                stream_message_callback=stream_message_callback,
            )

            if response:
                # Use client's response processing method
                assistant_response_text, should_break = (
                    current_llm_client.process_llm_response(
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
                tool_calls_info = current_llm_client.extract_tool_calls_info(
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
            await self._stream_tool_call("show_error", {"error": f"LLM Response Error: {purpose} timed out"}, True)
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
            await self._stream_tool_call("show_error", {"error": f"LLM Response Error: {purpose} {str(e)}"}, True)
            self.task_log.log_step(
                f"{purpose.lower().replace(' ', '_')}_error",
                f"{purpose} failed: {str(e)}",
                "failed",
            )
            return None, True, None

    async def _handle_summary_with_context_limit_retry(
        self,
        system_prompt,
        agent_prompt_instance,
        message_history,
        tool_definitions,
        purpose,
        task_description,
        task_failed,
        agent_type="main",
        task_guidence="",
        stream_message_callback: Callable = None
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
            summary_prompt = agent_prompt_instance.generate_summarize_prompt(
                task_description + task_guidence,
                task_failed=task_failed,
                chinese_context=self.chinese_context,
            )
            if self.debug_config and self.debug_config.get("summaryPrompt"):
                summary_prompt = self.debug_config.get("summaryPrompt")
                logger.info(f"Using custom summary prompt: {summary_prompt}")

            # Handle merging of message history and summary prompt
            current_llm_client = (
                self.llm_client if agent_type == "main" else self.sub_agent_llm_client
            )
            summary_prompt = current_llm_client.handle_max_turns_reached_summary_prompt(
                message_history, summary_prompt
            )

            # Directly add summary prompt to message history
            message_history.append(
                {"role": "user", "content": [{"type": "text", "text": summary_prompt}]}
            )

            for network_retry_count in range(5):
                (
                    response_text,
                    _,
                    tool_calls_info,
                ) = await self._handle_llm_call_with_logging(
                    system_prompt,
                    message_history,
                    tool_definitions,
                    999,
                    purpose,
                    agent_type=agent_type,
                    stream_message_callback=stream_message_callback
                )
                if response_text or tool_calls_info == "context_limit":
                    break
                else:
                    logger.error(
                        f"LLM summary process call failed, attempt {network_retry_count+1}/5, retrying after 60 seconds..."
                    )
                    self.task_log.log_step(
                        f"{agent_type}_summary_retry",
                        f"LLM summary process call failed, attempt {network_retry_count+1}/5, retrying after 60 seconds...",
                        "warning",
                    )
                    await asyncio.sleep(60)

            if response_text:
                # Call successful: return generated summary text
                return response_text

            # Context limit exceeded or network issues: try removing messages and retry
            retry_count += 1
            logger.debug(
                f"LLM call failed (context_limit), attempt {retry_count} retry, removing recent assistant-user dialogue"
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
        logger.error(
            "Summary failed after several attempts (removing all possible messages)"
        )
        self.task_log.log_step(
            f"{agent_type}_summary_failed",
            "Summary failed after several attempts (removing all possible messages)",
            "failed",
        )
        return "[ERROR] Unable to generate final summary due to context limit or network issues. You should try again."

    async def run_sub_agent(
        self, sub_agent_name, task_description, keep_tool_result: int = -1
    ):
        """
        Run sub agent
        """
        logger.debug(f"\n=== Starting Sub Agent {sub_agent_name} ===")
        task_description += "\n\nPlease provide the answer and detailed supporting information of the subtask given to you."
        logger.debug(f"Subtask: {task_description}")

        # Stream sub-agent start
        display_name = sub_agent_name.replace('agent-', '')
        sub_agent_id = await self._stream_start_agent(display_name)
        await self._stream_start_llm(display_name)


        # Start new sub-agent session
        self.task_log.start_sub_agent_session(sub_agent_name, task_description)

        # Simplified initial user content (no file attachments)
        initial_user_content = [{"type": "text", "text": task_description}]
        message_history = [{"role": "user", "content": initial_user_content}]

        # 获取sub-agent的工具定义
        if not self.sub_agent_tool_definitions:
            tool_definitions = await self._list_sub_agent_tools()
            tool_definitions = tool_definitions.get(sub_agent_name, [])
        else:
            tool_definitions = self.sub_agent_tool_definitions[sub_agent_name]
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
        if not self.cfg.sub_agents or sub_agent_name not in self.cfg.sub_agents:
            raise ValueError(f"Sub-agent {sub_agent_name} not found in configuration")
        sub_agent_prompt_instance = _load_agent_prompt_class(
            self.cfg.sub_agents[sub_agent_name].prompt_class
        )
        system_prompt = sub_agent_prompt_instance.generate_system_prompt_with_mcp_tools(
            mcp_servers=tool_definitions,
            chinese_context=self.chinese_context,
        )

        # Limit sub-agent turns
        max_turns = self.cfg.sub_agents[sub_agent_name].max_turns
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
                stream_message_callback=self._intercept_key_message,
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
            if (
                tool_calls is None
                or len(tool_calls) < 2
                or (len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0)
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
            max_tool_calls = self.cfg.sub_agents[sub_agent_name].max_tool_calls_per_turn
            tool_calls_exceeded = (
                len(tool_calls) > 0 and len(tool_calls[0]) > max_tool_calls
            )
            if tool_calls_exceeded:
                logger.warning(
                    f"[ERROR] Sub agent single turn tool call count too high ({len(tool_calls[0])} calls), only processing first {max_tool_calls}"
                )

            for call in tool_calls[0][:max_tool_calls]:
                # This place can be used to inject arguments of tools
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
                    tool_call_id = await self._stream_tool_call(tool_name, arguments)
                    tool_result = await self.sub_agent_tool_managers[
                        sub_agent_name
                    ].execute_tool_call(server_name, tool_name, arguments)
                    tool_result = self.post_process_tool_call_result(tool_name,tool_result)
                    result = tool_result.get("result") if tool_result.get("result") else tool_result.get("error")
                    await self._stream_tool_call(tool_name, {"result": result }, tool_call_id=tool_call_id)
                    # Stream usage info for tool call (tool calls don't have usage, just report tool name)
                    await self._stream_usage_info(sub_agent_name, {"tool_name": tool_name}, "tool_call")
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
                        "[ERROR]: Tool execution timeout"
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

            if len(tool_calls) > 1 and len(tool_calls[1]) > 0:
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

            message_history = self.sub_agent_llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded
            )

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

        await self._stream_tool_call("Partial Summary", {}, tool_call_id=str(uuid.uuid4()))


        # Use context limit retry logic to generate final summary
        final_answer_text = await self._handle_summary_with_context_limit_retry(
            system_prompt,
            sub_agent_prompt_instance,
            message_history,
            tool_definitions,
            f"Sub agent {sub_agent_name} final summary",
            task_description,
            task_failed,
            agent_type=sub_agent_name,
            stream_message_callback=self._intercept_key_message
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

        # Stream sub-agent end (usage will be reported together with main agent at the end)
        await self._stream_end_llm(display_name)
        await self._stream_end_agent(display_name, sub_agent_id)

        # Return final answer instead of dialogue log, so main agent can use directly
        return final_answer_text

    async def run_main_agent(
        self, task_description, task_file_name=None, task_id="default_task", history=None, extra_context: str = ""
    ):
        """
        Execute the main end-to-end task.
        """
        workflow_id = await self._stream_start_workflow(task_description,  task_id )
        keep_tool_result = int(self.cfg.main_agent.keep_tool_result)

        logger.debug(f"\n{'=' * 20} Starting Task: {task_id} {'=' * 20}")
        logger.debug(f"Task Description: {task_description}")
        if task_file_name:
            logger.debug(f"Associated File: {task_file_name}")

        # 1. Process input
        initial_user_content, task_description = process_input(
            task_description, task_file_name
        )

        task_guidence = ""

        # Add Chinese-specific guidance if enabled
        if self.chinese_context:
            task_guidence += """

## 中文任务处理指导

如果任务涉及中文语境，请遵循以下指导：

- **信息收集策略**：使用中文关键词进行网络搜索，优先浏览中文网页，以获取更准确和全面的中文资源
- **思考过程**：所有分析、推理、判断等思考过程都应使用中文表达，保持语义的一致性
- **候选答案收集**：对于中文问题，收集所有可能的中文答案选项，包括不同的表达方式和格式
- **证据文档化**：保持中文资源的原始格式，避免不必要的翻译或改写，确保信息的准确性
- **不确定性标注**：使用中文清晰地标记任何不确定性、冲突信息或需要进一步验证的内容
- **结果组织**：以中文组织和呈现最终报告，使用恰当的中文术语和表达习惯
- **过程透明化**：所有步骤描述、状态更新、中间结果等都应使用中文，确保用户理解
"""

        initial_user_content[0]["text"] = (
            initial_user_content[0]["text"] + task_guidence
        )

        hint_notes = ""  # Initialize hint_notes
        if self.cfg.main_agent.input_process.hint_generation:
            # Execute hint generation
            try:
                hint_content = await extract_hints(
                    task_description,
                    self.cfg.main_agent.openai_api_key,
                    self.chinese_context,
                    self.add_message_id,
                    self.cfg.main_agent.input_process.get(
                        "hint_llm_base_url", "https://api.openai.com/v1"
                    ),
                )
                hint_notes = (
                    "\n\nBefore you begin, please review the following preliminary notes highlighting subtle or easily misunderstood points in the question, which might help you avoid common pitfalls during your analysis (for reference only; these may not be exhaustive):\n\n"
                    + hint_content
                )

                # Update initial user content
                original_text = initial_user_content[0]["text"]
                initial_user_content[0]["text"] = original_text + hint_notes
            except Exception as e:
                logger.error(f"Hint generation failed after retries: {str(e)}")
                self.task_log.log_step(
                    step_name="hint_generation",
                    message=f"[ERROR] Hint generation failed: {str(e)}",
                    status="failed",
                )
                hint_notes = ""  # Continue execution but without hints

        logger.info("Initial user input content: %s", initial_user_content)
        
        message_history = []
        
        if history:
            initial_user_content = make_muti_turn_prompt(history, task_description)
            logger.info(f"Multi-turn prompt: {initial_user_content}")
            

        message_history.append({"role": "user", "content": initial_user_content})

        # 2. 获取工具定义
        if not self.tool_definitions:
            tool_definitions = await self.main_agent_tool_manager.get_all_tool_definitions()
            if self.cfg.sub_agents is not None and self.cfg.sub_agents:
                tool_definitions += expose_sub_agents_as_tools(self.cfg.sub_agents)
        else:
            tool_definitions = self.tool_definitions
        if not tool_definitions:
            logger.debug(
                "Warning: No tool definitions found. LLM cannot use any tools."
            )

        self.task_log.log_step("get_main_tool_definitions", f"{tool_definitions}")

        # 3. Generate system prompt
        main_agent_prompt_instance = _load_agent_prompt_class(
            self.cfg.main_agent.prompt_class
        )
        system_prompt = (
            main_agent_prompt_instance.generate_system_prompt_with_mcp_tools(
                mcp_servers=tool_definitions,
                chinese_context=self.chinese_context,
                extra_context=extra_context,
            )
        )

        # 4. Main loop: LLM <-> Tools
        max_turns = self.cfg.main_agent.max_turns
        if max_turns < 0:
            max_turns = sys.maxsize
        turn_count = 0
        task_failed = False  # Track whether task failed
        self.current_agent_id = await self._stream_start_agent("main")
        await self._stream_start_llm("main")
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
                stream_message_callback=self._intercept_key_message,
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

            if (
                tool_calls is None
                or len(tool_calls) < 2
                or (len(tool_calls[0]) == 0 and len(tool_calls[1]) == 0)
            ):
                # No tool calls, consider as final answer
                logger.debug("LLM did not request tool use, process ends.")
                break  # Exit loop

            # 7. Execute tool calls (in sequence)
            tool_calls_data = []
            all_tool_results_content_with_id = []

            # Get maximum tool calls per turn from configuration
            max_tool_calls = self.cfg.main_agent.max_tool_calls_per_turn
            tool_calls_exceeded = (
                len(tool_calls) > 0 and len(tool_calls[0]) > max_tool_calls
            )
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
                        # 进入到子 agent
                        await self._stream_end_llm("main")
                        await self._stream_end_agent("main", self.current_agent_id)
                        sub_agent_result = await self.run_sub_agent(
                            server_name, str(arguments), keep_tool_result
                        )
                        tool_result = {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "result": sub_agent_result,
                        }
                        # 重新进入主 agent
                        self.current_agent_id = await self._stream_start_agent("main", display_name="Summarizing")
                        await self._stream_start_llm("main", display_name="Summarizing")
                    else:
                        tool_call_id = await self._stream_tool_call(tool_name,arguments)
                        tool_result = (
                            await self.main_agent_tool_manager.execute_tool_call(
                                server_name=server_name,
                                tool_name=tool_name,
                                arguments=arguments,
                            )
                        )
                        tool_result = self.post_process_tool_call_result(tool_name,tool_result)
                        result = tool_result.get("result") if tool_result.get("result") else tool_result.get("error")
                        await self._stream_tool_call(tool_name,{"result": result}, tool_call_id=tool_call_id)
                        # Stream usage info for tool call (tool calls don't have usage, just report tool name)
                        await self._stream_usage_info("main", {"tool_name": tool_name}, "tool_call")

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
                        "[ERROR]: Tool execution timeout"
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

            if len(tool_calls) > 1 and len(tool_calls[1]) > 0:
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
        

        # 退出主 llm,agent
        await self._stream_end_llm("main")
        await self._stream_end_agent("main", self.current_agent_id)

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

        self.current_agent_id = await self._stream_start_agent("reporter")
        await self._stream_start_llm("reporter")

        # Use context limit retry logic to generate final summary
        final_answer_text = await self._handle_summary_with_context_limit_retry(
            system_prompt,
            main_agent_prompt_instance,
            message_history,
            tool_definitions,
            "Final summary generation",
            task_description,
            task_failed,
            agent_type="main",
            task_guidence=task_guidence,
            stream_message_callback=self._streaming_final_message,
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

            # Use LLM to extract final answer
            extracted_answer = ""
            if self.cfg.main_agent.output_process.final_answer_extraction:
                # Execute final answer extraction
                try:
                    # For browsecomp-zh, we use another Chinese prompt to extract the final answer
                    if "browsecomp-zh" in self.cfg.benchmark.name:
                        extracted_answer = await extract_browsecomp_zh_final_answer(
                            task_description,
                            final_answer_text,
                            self.cfg.main_agent.openai_api_key,
                            self.cfg.main_agent.output_process.get(
                                "final_answer_llm_base_url", "https://api.openai.com/v1"
                            ),
                        )

                        # Disguise LLM extracted answer as assistant returned result and add to message history
                        assistant_extracted_message = {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"LLM extracted final answer:\n{extracted_answer}",
                                }
                            ],
                        }
                        message_history.append(assistant_extracted_message)

                        # LLM answer as final result
                        final_answer_text = extracted_answer
                    else:
                        extracted_answer = await extract_gaia_final_answer(
                            task_description,
                            final_answer_text,
                            self.cfg.main_agent.openai_api_key,
                            self.chinese_context,
                            self.cfg.main_agent.output_process.get(
                                "final_answer_llm_base_url", "https://api.openai.com/v1"
                            ),
                        )

                        # Disguise LLM extracted answer as assistant returned result and add to message history
                        assistant_extracted_message = {
                            "role": "assistant",
                            "content": [
                                {
                                    "type": "text",
                                    "text": f"LLM extracted final answer:\n{extracted_answer}",
                                }
                            ],
                        }
                        message_history.append(assistant_extracted_message)

                        # Concatenate original summary and LLM answer as final result
                        final_answer_text = f"{final_answer_text}\n\nLLM Extracted Answer:\n{extracted_answer}"

                except Exception as e:
                    logger.error(
                        f"Final answer extraction failed after retries: {str(e)}"
                    )
                    self.task_log.log_step(
                        step_name="final_answer_extraction",
                        message=f"[ERROR] Final answer extraction failed: {str(e)}",
                        status="failed",
                    )
                    # Continue using original final_answer_text

            else:
                # to process when final_answer_extraction is false
                # leave it here to be more clear
                final_answer_text = final_answer_text

        else:
            final_answer_text = "No final answer generated."
            self.task_log.log_step(
                "final_answer", "Failed to extract final answer", "failed"
            )

        logger.debug(f"LLM Final Answer: {final_answer_text}")

        # Save final message history (including LLM processing results)
        self.task_log.main_agent_message_history = {
            "system_prompt": system_prompt,
            "message_history": message_history,
        }
        self.task_log.save()

        # Format and return final output
        self.task_log.log_step("format_output", "Formatting final output")
        final_summary, final_boxed_answer = (
            self.output_formatter.format_final_summary_and_log(
                final_answer_text, self.llm_client
            )
        )
        await self._stream_end_llm("reporter")
        await self._stream_end_agent("reporter", self.current_agent_id)
        # Stream usage info for main agent
        main_agent_usage = self.llm_client.get_usage()
        await self._stream_usage_info("main", main_agent_usage, "main_agent_end")
        
        # Stream usage info for sub agents if they use a different client
        if self.sub_agent_llm_client and self.sub_agent_llm_client is not self.llm_client:
            sub_agent_usage = self.sub_agent_llm_client.get_usage()
            await self._stream_usage_info("sub_agent", sub_agent_usage, "sub_agent_end")
        
        await self._stream_end_workflow(workflow_id)

        logger.debug(f"\n{'=' * 20} Task {task_id} Finished {'=' * 20}")
        self.task_log.log_step(
            "task_completed", f"Main agent task {task_id} completed successfully"
        )

        if "browsecomp-zh" in self.cfg.benchmark.name:
            return final_summary, final_summary
        else:
            return final_summary, final_boxed_answer
