# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses
import json
import os
from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from omegaconf import DictConfig

from src.logging.logger import bootstrap_logger
from src.logging.task_tracer import TaskTracer

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


@dataclasses.dataclass
class LLMProviderClientBase(ABC):
    # Required arguments (no default value)
    task_id: str
    cfg: DictConfig

    # Optional arguments (with default value)
    task_log: Optional["TaskTracer"] = None

    # post_init
    client: Any = dataclasses.field(init=False)

    def __post_init__(self):
        # Explicitly assign from cfg object
        self.provider_class: str = self.cfg.llm.provider_class
        self.model_name: str = self.cfg.llm.model_name
        self.temperature: float = self.cfg.llm.temperature
        self.top_p: float = self.cfg.llm.top_p
        self.min_p: float = self.cfg.llm.min_p
        self.top_k: int = self.cfg.llm.top_k
        self.reasoning_effort: str = self.cfg.llm.get("reasoning_effort", "medium")
        self.repetition_penalty: float = self.cfg.llm.get("repetition_penalty", 1.0)
        self.max_tokens: int = self.cfg.llm.max_tokens
        self.max_context_length: int = self.cfg.llm.get("max_context_length", -1)
        self.oai_tool_thinking: bool = self.cfg.llm.oai_tool_thinking
        self.async_client: bool = self.cfg.llm.async_client

        self.use_tool_calls: Optional[bool] = self.cfg.llm.get("use_tool_calls")
        self.openrouter_provider: Optional[str] = self.cfg.llm.get(
            "openrouter_provider"
        )
        # Safely handle string to bool conversion
        disable_cache_control_val = self.cfg.llm.get("disable_cache_control", False)
        if isinstance(disable_cache_control_val, str):
            self.disable_cache_control: bool = (
                disable_cache_control_val.lower().strip() == "true"
            )
        else:
            self.disable_cache_control: bool = bool(disable_cache_control_val)

        logger.info(
            f"openrouter_provider config value: {self.openrouter_provider} (type: {type(self.openrouter_provider)})"
        )

        logger.info(
            f"disable_cache_control config value: {disable_cache_control_val} (type: {type(disable_cache_control_val)}) -> parsed as: {self.disable_cache_control}"
        )

        self.client = self._create_client(self.cfg)

        logger.info(
            f"LLMClient (class={self.__class__.__name__},provider={self.provider_class},model_name={self.model_name}) initialized"
        )

    @abstractmethod
    def _create_client(self, config: DictConfig) -> Any:
        """Create specific LLM client"""
        raise NotImplementedError("must override in subclass")

    @abstractmethod
    async def _create_message(
        self,
        system_prompt: str,
        messages: List[Dict],
        tools_definitions: List[Dict],
        keep_tool_result: int = -1,
    ) -> Any:
        """Create provider-specific message - implemented by subclass"""
        raise NotImplementedError("subclass must implement this")

    @abstractmethod
    def process_llm_response(
        self, llm_response, message_history, agent_type="main"
    ) -> tuple[str, bool]:
        """Process LLM response - implemented by subclass"""
        pass

    @abstractmethod
    def extract_tool_calls_info(
        self, llm_response, assistant_response_text
    ) -> tuple[list, list]:
        """Extract tool call information - implemented by subclass"""
        pass

    def _remove_tool_result_from_messages(self, messages, keep_tool_result):
        messages_copy = [m.copy() for m in messages]
        """Remove tool results from messages"""
        if keep_tool_result >= 0:
            # Find indices of all user messages
            user_indices = [
                i
                for i, msg in enumerate(messages_copy)
                if msg.get("role") == "user" or msg.get("role") == "tool"
            ]

            if (
                len(user_indices) > 1
            ):  # Only proceed if there are more than one user message
                first_user_idx = user_indices[0]  # Always keep the first user message

                # Calculate how many messages to keep from the end
                # If keep_tool_result is 0, we only keep the first message
                num_to_keep = (
                    0
                    if keep_tool_result == 0
                    else min(keep_tool_result, len(user_indices) - 1)
                )

                # Get indices of messages to keep from the end
                last_indices_to_keep = (
                    user_indices[-num_to_keep:] if num_to_keep > 0 else []
                )

                # Combine first message and last k messages
                indices_to_keep = [first_user_idx] + last_indices_to_keep

                logger.debug("\n=======>>>>>> Message retention summary:")
                logger.debug(f"Total user messages: {len(user_indices)}")
                logger.debug(f"Keeping first message at index: {first_user_idx}")
                logger.debug(
                    f"Keeping last {num_to_keep} messages at indices: {last_indices_to_keep}"
                )
                logger.debug(f"Total messages to keep: {len(indices_to_keep)}")

                for i, msg in enumerate(messages_copy):
                    if (
                        msg.get("role") == "user" or msg.get("role") == "tool"
                    ) and i not in indices_to_keep:
                        logger.debug(f"Omitting content for user message at index {i}")
                        msg["content"] = "Tool result is omitted to save tokens."
            elif user_indices:  # This means only 1 user message exists
                logger.debug(
                    "\n=======>>>>>> Only 1 user message found. Keeping it as is."
                )
            else:  # No user messages at all
                logger.debug("\n=======>>>>>> No user messages found in the history.")

            logger.debug(
                f"\n\n=======>>>>>> Messages after potential content omission: {json.dumps(messages_copy, indent=4, ensure_ascii=False)}\n\n"
            )
        elif keep_tool_result == -1:
            # No processing
            pass

        return messages_copy

    async def create_message(
        self,
        system_prompt: str,
        message_history: List[Dict],
        tool_definitions: List[Dict],
        keep_tool_result: int = -1,
        step_id: int = 1,
        task_log: Optional["TaskTracer"] = None,
        agent_type: str = "main",
    ):
        """
        Call LLM to generate response, supports tool calls - unified implementation
        """
        # Filter message history
        filtered_history = self._filter_message_history(
            message_history, keep_tool_result
        )

        response = None

        # Unified LLM call handling
        response = await self._create_message(
            system_prompt,
            filtered_history,
            tool_definitions,
            keep_tool_result=keep_tool_result,
        )
        return response

    @staticmethod
    async def convert_tool_definition_to_tool_call(tools_definitions):
        tool_list = []
        for server in tools_definitions:
            if "tools" in server and len(server["tools"]) > 0:
                for tool in server["tools"]:
                    tool_def = dict(
                        type="function",
                        function=dict(
                            name=f"{server['name']}-{tool['name']}",
                            description=tool["description"],
                            parameters=tool["schema"],
                        ),
                    )
                    tool_list.append(tool_def)
        return tool_list

    def close(self):
        """Close client connection"""
        if hasattr(self.client, "close"):
            if asyncio.iscoroutinefunction(self.client.close):
                # For async clients, we can't directly call close here
                # Need to call it in an async function
                pass
            else:
                self.client.close()
        elif hasattr(self.client, "_client") and hasattr(self.client._client, "close"):
            # Some clients may have an internal _client attribute
            self.client._client.close()
        else:
            # If the client doesn't have a close method, or is async, we skip
            pass

    def _filter_message_history(
        self, message_history: List[Dict], keep_tool_result: int
    ) -> List[Dict]:
        """Filter message history, keep specified number of tool results"""
        if keep_tool_result == -1:
            return message_history

        # Complex filtering logic can be implemented here
        # For now, simply return the last keep_tool_result messages
        if keep_tool_result > 0 and len(message_history) > keep_tool_result:
            return message_history[-keep_tool_result:]
        return message_history

    def _format_response_for_log(self, response) -> Dict:
        """Format response for logging"""
        if not response:
            return {}

        # Basic response information
        formatted: dict[str, Any] = {
            "response_type": type(response).__name__,
        }

        # Anthropic response
        if hasattr(response, "content"):
            formatted["content"] = []
            for block in response.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        formatted["content"].append(
                            {
                                "type": "text",
                                "text": block.text[:500] + "..."
                                if len(block.text) > 500
                                else block.text,
                            }
                        )
                    elif block.type == "tool_use":
                        formatted["content"].append(
                            {
                                "type": "tool_use",
                                "id": block.id,
                                "name": block.name,
                                "input": str(block.input)[:200] + "..."
                                if len(str(block.input)) > 200
                                else str(block.input),
                            }
                        )

        # OpenAI response
        if hasattr(response, "choices"):
            formatted["choices"] = []
            for choice in response.choices:
                choice_data = {"finish_reason": choice.finish_reason}
                if hasattr(choice, "message"):
                    message = choice.message
                    choice_data["message"] = {
                        "role": message.role,
                        "content": message.content[:500] + "..."
                        if message.content and len(message.content) > 500
                        else message.content,
                    }
                    if hasattr(message, "tool_calls") and message.tool_calls:
                        choice_data["message"]["tool_calls_count"] = len(
                            message.tool_calls
                        )
                formatted["choices"].append(choice_data)

        return formatted

    @abstractmethod
    def update_message_history(
        self,
        message_history: list[dict[str, Any]],
        tool_call_info: list[Any],
        tool_calls_exceeded: bool = False,
    ):
        raise NotImplementedError("must implement in subclass")

    @abstractmethod
    def handle_max_turns_reached_summary_prompt(
        self, message_history: list[dict[str, Any]], summary_prompt: str
    ):
        raise NotImplementedError("must implement in subclass")
