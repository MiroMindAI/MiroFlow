# src/core/agent_runner.py

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Protocol, Optional, Sequence
import uuid
from omegaconf import DictConfig
from src.logging.logger import bootstrap_logger
from typing import Callable, Awaitable
import traceback
from contextlib import asynccontextmanager



from src.logging.task_tracer import TaskTracer
from src.tool.manager import ToolManager
from config.agent_prompts.base_agent_prompt import BaseAgentPrompt

#foundation
from src.llm.provider_client_base import LLMProviderClientBase
from src.llm.providers.claude_openrouter_client import ContextLimitError
from src.utils.io_utils import get_file_type
from src.utils.prompt_manager import PromptTemplateReader
from src.utils.tool_utils import create_mcp_server_parameters, expose_sub_agents_as_tools
from src.llm.client import LLMClient
from src.utils.io_utils import OutputFormatter
from src.utils.summary_utils import (
    extract_hints,
    extract_gaia_final_answer,
    extract_browsecomp_zh_final_answer
)
import time, datetime
from functools import cached_property


LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)

@dataclass(frozen=True)
class TaskInput:
    # task
    task_id: Optional[str] = None
    #task_log: TaskTracer
    task_description: Optional[str] = None
    task_file_name: Optional[str] = None
    
    @cached_property
    def task_file_type(self):
        return get_file_type(self.task_file_name)

AgentCaller = Callable[[str, TaskInput], Awaitable[str]]

@dataclass
class LLMCallError:
    log_suffix: str
    message: str
    status: str
    return_value: tuple

LLM_ERROR_HANDLERS = {
    asyncio.TimeoutError: lambda e, purpose: LLMCallError(
        "timeout", f"{purpose} timed out", "failed", (None, True, None)
    ),
    ContextLimitError: lambda e, purpose: LLMCallError(
        "context_limit", f"{purpose} context limit exceeded: {e}", "warning", (None, True, "context_limit")
    ),
}

class AgentNode(Protocol):
    def __init__(self, name: str, cfg: DictConfig, agent_caller: AgentCaller=None):
        self.config = cfg
        self.name = name

        if hasattr(cfg, "llm"):
            self.llm_client = LLMClient(task_id=None, llm_config=cfg.llm)
        if cfg.get("tool_config", None) is not None:
            mcp_server_configs, blacklist = create_mcp_server_parameters(
                cfg, logs_dir=None #TODO
            )
            self.tool_manager = ToolManager(
                mcp_server_configs,
                tool_blacklist=blacklist,
            )
        self.output_formatter = OutputFormatter()
        self.prompt_manager = PromptTemplateReader(config_path = cfg.prompt_config_path) 
        self.cfg = cfg
        self.add_message_id = True
        self.callable_agent_names = cfg.get("callable_agent_names", [])
        self.agent_caller = agent_caller

    @property
    def task_log(self) -> TaskTracer | None:
        """通过 contextvars 获取当前任务的 TaskTracer，支持并行执行"""
        from src.agents.orchestrator import get_current_task_log
        return get_current_task_log()

    # ---------------------------- tool definitions related functions ----------------------------
    @staticmethod
    def get_mcp_server_definitions_from_tool_definitions(tool_definitions: list[dict[str, Any]]) -> str:
        mcp_server_definitions = ""
        if tool_definitions and len(tool_definitions) > 0:
            for server in tool_definitions:
                mcp_server_definitions += f"## Server name: {server['name']}\n"
                if "tools" in server and len(server["tools"]) > 0:
                    for tool in server["tools"]:
                        mcp_server_definitions += f"### Tool name: {tool['name']}\n"
                        mcp_server_definitions += f"Description: {tool['description']}\n"
        return mcp_server_definitions
            #actions
    
    async def init_tool_definitions(self):
        tool_definitions = await self.tool_manager.get_all_tool_definitions()
        mcp_server_definitions = self.get_mcp_server_definitions_from_tool_definitions(tool_definitions)
        if len(self.callable_agent_names) > 0:
            subagent_server_definitions = expose_sub_agents_as_tools(self.callable_agent_names)
            mcp_server_definitions += self.get_mcp_server_definitions_from_tool_definitions(subagent_server_definitions)
        self.tool_definitions = tool_definitions
        self.mcp_server_definitions = mcp_server_definitions

    def _prepare_summary_prompt(self, message_history, task_description, task_failed):
        summary_prompt = self.prompt_manager.render_prompt(
            prompt_name='summarize_prompt',
            context = dict(task_description = task_description, task_failed = task_failed, chinese_context = False)
        )
        summary_prompt = self.llm_client.handle_max_turns_reached_summary_prompt(
            message_history, summary_prompt
        )
        return summary_prompt

    # ---------------------------- messages & prompt related functions ----------------------------
    async def _prepare_initial_messages(self, input: TaskInput):
        if input.task_file_name:
            file_input = dict(file_type = input.task_file_type, file_name = input.task_file_name,
            absolute_file_path = os.path.abspath(input.task_file_name))
        else:
            file_input = None
        initial_user_message = self.prompt_manager.render_prompt(
            prompt_name = 'initial_user_text',
            context = dict(task_description = input.task_description, file_input = file_input)
        )

        system_prompt = self.prompt_manager.render_prompt(  
            prompt_name='system_prompt',
            context = dict(formatted_date = datetime.datetime.now().strftime("%Y-%m-%d"), mcp_server_definitions = self.mcp_server_definitions)
        )
        return initial_user_message, system_prompt
 
    async def _extract_final_answer(self, final_answer_text, message_history, input):
        try:
            if "browsecomp-zh" in self.cfg: #TODO
                extracted_answer = await extract_browsecomp_zh_final_answer(
                    input.task_description,
                    final_answer_text,
                    self.cfg.openai_api_key,
                    self.cfg.output_process.get(
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
                    input.task_description,
                    final_answer_text,
                    self.cfg.openai_api_key,
                    False, #TODO
                    self.cfg.output_process.get(
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

                return final_answer_text

        except Exception as e:
            logger.error(
                f"Final answer extraction failed after retries: {str(e)}"
            )
            self.task_log.log_step(
                step_name="final_answer_extraction",
                message=f"[ERROR] Final answer extraction failed: {str(e)}",
                status="failed",
            )
            return None

    # ---------------------------- LLM call related functions ----------------------------
    def _handle_llm_error(self, error: Exception, purpose: str) -> tuple:
        """统一处理LLM调用异常"""
        handler = LLM_ERROR_HANDLERS.get(type(error))
        if handler:
            err = handler(error, purpose)
        else:
            err = LLMCallError("error", f"{purpose} failed: {error}", "failed", (None, True, None))
        
        logger.debug(f'{err.message}')
        self.task_log.log_step(f"{purpose.lower().replace(' ', '_')}_{err.log_suffix}", err.message, err.status)
        return err.return_value
    
    @asynccontextmanager
    async def _llm_call_logging_context(self, agent_call_id: str, system_prompt, message_history):
        """管理LLM调用前后的日志保存"""
        if self.task_log:
            self.task_log.message_history[agent_call_id] = {
                "system_prompt": system_prompt,
                "message_history": message_history,
            }
            self.task_log.save()
        try:
            yield
        finally:
            if self.task_log:
                self.task_log.message_history[agent_call_id] = {
                    "system_prompt": system_prompt,
                    "message_history": message_history,
                }
                self.task_log.save()

    async def _call_llm(
        self,
        system_prompt,
        message_history,
        tool_definitions,
    ) -> tuple[str | None, bool, Any | None]:
        """执行LLM调用并返回处理后的响应"""
        response = await self.llm_client.create_message(
            system_prompt=system_prompt,
            message_history=message_history,
            tool_definitions=tool_definitions,
            keep_tool_result=self.cfg.keep_tool_result
        )
        
        if not response:
            return None, True, None
        
        # 1. 处理响应（不再隐式修改 message_history）
        response_text, invalid_response, assistant_message = self.llm_client.process_llm_response(
            response
        )
        
        # 2. 显式更新 message_history（调用者清楚知道发生了什么）
        if assistant_message:
            message_history.append(assistant_message)
        
        # 3. 提取工具调用信息
        tool_calls_info = self.llm_client.extract_tool_calls_info(response, response_text)
        
        return response_text, invalid_response, tool_calls_info

    async def _handle_llm_call_with_logging(
        self,
        system_prompt,
        message_history,
        tool_definitions,
        purpose: str,
        agent_call_id: str,
    ) -> tuple[str | None, bool, Any | None]:
        if self.config.add_message_id:
            self.llm_client._inject_message_ids(message_history)
        
        async with self._llm_call_logging_context(agent_call_id, system_prompt, message_history):
            try:
                response_text, invalid_response, tool_calls = await self._call_llm(
                    system_prompt, message_history, tool_definitions
                )
            except Exception as e:
                return self._handle_llm_error(e, purpose)
    
        return response_text, invalid_response, tool_calls

    async def _handle_llm_call_with_context_limit_retry(
        self,
        system_prompt,
        message_history,
        tool_definitions,
        purpose: str,
        agent_call_id
    ):
        retry_count = 0

        while True:
            current_llm_client = self.llm_client
   
            for network_retry_count in range(5):
                (
                    response_text,
                    _,
                    tool_calls_info,
                ) = await self._handle_llm_call_with_logging(
                    system_prompt,
                    message_history,
                    tool_definitions,
                    purpose,
                    agent_call_id
                )
                if response_text or tool_calls_info == "context_limit":
                    break
                else:
                    logger.error(
                        f"{purpose} process call failed, attempt {network_retry_count+1}/5, retrying after 60 seconds..."
                    )
                    self.task_log.log_step(
                        purpose,
                        f"{purpose} process call failed, attempt {network_retry_count+1}/5, retrying after 60 seconds...",
                        "warning",
                    )
                    await asyncio.sleep(60)

            if response_text:
                # Call successful: return generated summary text
                return response_text

            # Context limit exceeded or network issues: try removing messages and retry
            retry_count += 1
            # First remove the just-added summary prompt
            if message_history and message_history[-1]["role"] == "user":
                message_history.pop()
            # Remove the most recent assistant message (tool call request)
            if message_history and message_history[-1]["role"] == "assistant":
                message_history.pop()
            # If there are no more dialogues to remove
            if len(message_history) <= 2:  # Only initial system-user messages remain
                logger.warning(
                    "Removed all removable dialogues, but still unable to generate summary"
                )
                break
            self.task_log.log_step(
                purpose,
                f"Removed assistant-user pair, retry {retry_count}",
                "warning",
            )

        # If still fails after removing all dialogues
        logger.error(
            f"{purpose} failed after several attempts (removing all possible messages)"
        )
        self.task_log.log_step(
            purpose,
            f"{purpose} failed after several attempts (removing all possible messages)",
            "failed",
        )
        return f"[ERROR] {purpose} failed due to context limit or network issues. You should try again."

    # ---------------------------- tool call related functions ----------------------------
    def _handle_tool_error(self, error: Exception, call: dict) -> dict:
        logger.error(f"Tool execution failed: {error}\nTraceback: {traceback.format_exc()}")
        
        error_msg = str(error) or (
            "[ERROR]: Tool execution timeout"
            if isinstance(error, TimeoutError)
            else f"Tool execution failed: {type(error).__name__}"
        )
        return {
            "server_name": call["server_name"],
            "tool_name": call["tool_name"],
            "error": error_msg,
        }
    
    async def _execute_single_tool_call(
        self, 
        call: dict, 
        input: TaskInput
    ) -> tuple[str, str]:
        try:
            server_name = call["server_name"]
            tool_name = call["tool_name"]
        
            if server_name in self.callable_agent_names:
                result = await self.agent_caller(
                    server_name, 
                    TaskInput(task_description=input.task_description)
                )
                result = {"server_name": server_name, "tool_name": tool_name, "result": result}
            else:
                result = await self.tool_manager.execute_tool_call(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=call["arguments"],
                )
        except Exception as e:
            result = self._handle_tool_error(e, call)
        
        formatted = self.output_formatter.format_tool_result_for_user(result)
        return call["id"], formatted

    def _has_tool_calls(self, tool_calls: tuple) -> bool:
        return (
            tool_calls is not None
            and len(tool_calls) >= 2
            and (len(tool_calls[0]) > 0 or len(tool_calls[1]) > 0)
        )

    async def _execute_tool_calls_batch(
        self,
        tool_calls: tuple,
        input: TaskInput,
    ) -> tuple[list[tuple[str, str]], bool]:
        calls = tool_calls[0]
        max_tool_calls = self.cfg.max_tool_calls_per_turn
        exceeded = len(calls) > max_tool_calls
        
        if exceeded:
            logger.warning(
                f"[WARNING] Tool calls ({len(calls)}) exceed limit, processing first {max_tool_calls}"
            )
            calls = calls[:max_tool_calls]
        
        results = []
        for call in calls:
            result = await self._execute_single_tool_call(call, input)
            results.append(result)
        
        return results, exceeded

    # ---------------------------- entrypoint ----------------------------
    async def run(self, input: TaskInput, call_info: dict) -> str:
        agent_call_id = f"{self.name}.call_{call_info['called_count']}"
        
        initial_user_message, system_prompt = await self._prepare_initial_messages(input)
        
        message_history = [{"role": "user", "content": initial_user_message}] #TODO

        #main loop
        task_failed = False
        turn_count = 0
        max_turns = self.config.max_turns

        while max_turns == -1 or turn_count < max_turns:
            turn_count += 1
            logger.debug(f"\n--- {agent_call_id} turn {turn_count} ---")
            self.task_log.save()

            (
                assistant_response_text,
                invalid_response,
                tool_calls,
            ) = await self._handle_llm_call_with_logging(
                system_prompt,
                message_history,
                self.tool_definitions,
                f"{agent_call_id}_turn_{turn_count}",
                agent_call_id=agent_call_id
            )

            if invalid_response:
                task_failed = True
                break
            if not self._has_tool_calls(tool_calls):
                # No tool calls, consider as final answer
                logger.debug("LLM did not request tool use, process ends.")
                break  # Exit loop

            all_tool_results_content_with_id, tool_calls_exceeded = await self._execute_tool_calls_batch(
                tool_calls, input
            )
            message_history = self.llm_client.update_message_history(
                message_history, all_tool_results_content_with_id, tool_calls_exceeded #TODO
            ) #TODO

        message_history.append(
            {
                "role": "user", 
                "content": [{
                    "type": "text",
                    "text": self._prepare_summary_prompt(message_history, input.task_description, task_failed)}
                ]
            }
        ) #TODO
        summary = await self._handle_llm_call_with_context_limit_retry(
            system_prompt = system_prompt,
            message_history = message_history,
            tool_definitions = self.tool_definitions,
            purpose = f"{agent_call_id}_summary",
            agent_call_id = agent_call_id
        )
        
        if self.cfg.get('output_process',{}).get('final_answer_extraction',False):
            summary = await self._extract_final_answer(
                summary, message_history, input
            )
        if self.cfg.get('output_process',{}).get('format_final_summary',False):
            summary, final_boxed_answer = self.output_formatter.format_final_summary_and_log(
                summary, self.llm_client
            )

        return summary


