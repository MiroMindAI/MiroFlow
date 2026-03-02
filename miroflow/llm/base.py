# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
LLM client base class module
"""

import asyncio
import dataclasses
import json
import re
from abc import ABC, abstractmethod
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from omegaconf import DictConfig

from miroflow.logging.task_tracer import get_tracer
from miroflow.logging.decorators import span
import uuid

logger = get_tracer()


class ContextLimitError(Exception):
    """Context limit exceeded - non-retriable."""

    pass


@dataclasses.dataclass
class LLMOutput(ABC):
    """LLM output data class"""

    response_text: str
    is_invalid: bool
    assistant_message: dict
    raw_response: Any


class LLMClientBase(ABC):
    """LLM client base class"""

    def __init__(self, cfg: DictConfig):
        self.cfg = cfg

        # Explicitly assign from cfg object
        self.provider_class: str = self.cfg.provider_class
        self.model_name: str = self.cfg.model_name
        self.temperature: float = self.cfg.temperature
        self.top_p: float = self.cfg.top_p
        self.min_p: float = self.cfg.min_p
        self.top_k: int = self.cfg.top_k
        self.reasoning_effort: str = self.cfg.reasoning_effort
        self.repetition_penalty: float = self.cfg.repetition_penalty
        self.max_tokens: int = self.cfg.max_tokens
        self.max_context_length: int = self.cfg.max_context_length
        self.async_client: bool = self.cfg.async_client

        # Token usage tracking for proactive context limit management
        self.last_call_tokens: dict = {}

        self.use_tool_calls: Optional[bool] = self.cfg.use_tool_calls
        self.disable_cache_control: bool = self.cfg.disable_cache_control
        self.keep_tool_result: int = self.cfg.get("keep_tool_result", -1)
        self.strip_think_from_history: bool = self.cfg.get(
            "strip_think_from_history", False
        )

        self.client = self._create_client(self.cfg)

        logger.info(
            f"LLMClient (class={self.__class__.__name__},provider={self.provider_class},model_name={self.model_name}) (cfg={self.cfg}) initialized"
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
    def process_llm_response(self, llm_response) -> tuple[str, bool, dict]:
        """
        Process LLM response - implemented by subclass

        Returns:
            tuple[str, bool, dict]: (response_text, is_invalid, assistant_message)
            - response_text: The text content of the response
            - is_invalid: Whether the response is invalid and should break the loop
            - assistant_message: The message dict to append to message_history

        Note:
            This method no longer modifies message_history in-place.
            The caller is responsible for appending assistant_message to message_history.
        """
        pass

    @abstractmethod
    def extract_tool_calls_info(
        self, llm_response, assistant_response_text
    ) -> tuple[list, list]:
        """Extract tool call information - implemented by subclass"""
        pass

    def _strip_think_from_messages(self, messages: List[Dict]) -> List[Dict]:
        """Strip <think>...</think> blocks from assistant messages."""
        think_pattern = re.compile(r"<think>.*?</think>\s*", re.DOTALL)
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if isinstance(content, str):
                    msg["content"] = think_pattern.sub("", content)
        return messages

    def _remove_tool_result_from_messages(
        self, messages, keep_tool_result, strip_think=False
    ):
        """Remove tool results from messages and optionally strip think blocks."""
        messages_copy = [m.copy() for m in messages]

        if strip_think:
            messages_copy = self._strip_think_from_messages(messages_copy)

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

    @span()
    async def create_message(
        self,
        message_text: str = None,
        system_prompt: str = None,
        message_history: List[Dict] = None,
        tool_definitions: List[Dict] = None,
        keep_tool_result: int = None,
    ):
        """
        Call LLM to generate response, supports tool calls - unified implementation
        """
        assert (
            message_text is not None or message_history is not None
        ), "Either message_text or message_history must be provided"
        assert (
            message_text is None or message_history is None
        ), "Only one of message_text or message_history can be provided"

        # Use config value if not explicitly provided
        if keep_tool_result is None:
            keep_tool_result = self.keep_tool_result

        if message_history is None:
            message_history = []
        if message_text is not None:
            message_history.append(
                {"role": "user", "content": [{"type": "text", "text": message_text}]}
            )

        response = None

        # Unified LLM call handling
        response = await self._create_message(
            system_prompt=system_prompt,
            messages=message_history,
            tools_definitions=tool_definitions,
            keep_tool_result=keep_tool_result,
        )
        response_text, is_invalid, assistant_message = self.process_llm_response(
            response
        )
        return LLMOutput(
            response_text=response_text,
            is_invalid=is_invalid,
            assistant_message=assistant_message,
            raw_response=response,
        )

    @staticmethod
    async def convert_tool_definition_to_tool_call(tools_definitions):
        tool_list = []
        # Handle None case (when SummaryGenerator or other components don't provide tools)
        if tools_definitions is None:
            return tool_list

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
                logger.debug(
                    "Skipping async client close — must be called from async context"
                )
            else:
                self.client.close()
        elif hasattr(self.client, "_client") and hasattr(self.client._client, "close"):
            # Some clients may have an internal _client attribute
            self.client._client.close()
        else:
            # If the client doesn't have a close method, or is async, we skip
            logger.debug("Client has no close method, skipping cleanup")

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

    def _inject_message_ids(self, message_history: list[dict]) -> None:
        """Inject unique message IDs to user messages to avoid cache hits"""

        def _generate_message_id() -> str:
            """Generate random message ID using common LLM format"""
            # Use 8-character random hex string, similar to OpenAI API format, avoid cross-conversation cache hits
            return f"msg_{uuid.uuid4().hex[:8]}"

        for message in message_history:
            if message.get("role") != "user":
                continue
            content = message.get("content")
            if isinstance(content, list):
                for item in content:
                    if item.get("type") == "text" and not item["text"].startswith(
                        "[msg_"
                    ):
                        item["text"] = f"[{_generate_message_id()}] {item['text']}"
            elif isinstance(content, str) and not content.startswith("[msg_"):
                message["content"] = f"[{_generate_message_id()}] {content}"

    def _estimate_tokens(self, text: str) -> int:
        """Default token estimation. Subclasses can override with tiktoken."""
        return len(text) // 4

    def ensure_summary_context(
        self, message_history: list, summary_prompt: str
    ) -> tuple[bool, list]:
        """
        Check if the context still has room for a summary call.
        If not, remove the last assistant-user pair from message_history.

        Returns:
            (can_continue, message_history):
              - can_continue=True means there is still room, continue the loop
              - can_continue=False means context is near limit, break the loop
        """
        # If max_context_length is not set (<=0), skip the check entirely
        if self.max_context_length <= 0:
            return True, message_history

        # If no token usage recorded yet (first call), skip the check
        last_prompt_tokens = self.last_call_tokens.get("prompt_tokens", 0)
        last_completion_tokens = self.last_call_tokens.get("completion_tokens", 0)
        if last_prompt_tokens == 0:
            return True, message_history

        buffer_factor = 1.5

        # Estimate tokens for the summary prompt
        summary_tokens = int(self._estimate_tokens(summary_prompt) * buffer_factor)

        # Estimate tokens for the last user message (most recent tool result)
        last_user_content = ""
        if message_history and message_history[-1].get("role") == "user":
            content = message_history[-1].get("content", "")
            if isinstance(content, list):
                last_user_content = " ".join(
                    item.get("text", "")
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                )
            elif isinstance(content, str):
                last_user_content = content
        last_user_tokens = int(self._estimate_tokens(last_user_content) * buffer_factor)

        # Estimate total: previous context + new completion + summary ability
        estimated_total = (
            last_prompt_tokens
            + last_completion_tokens
            + last_user_tokens
            + summary_tokens
            + self.max_tokens
            + 1000  # safety buffer
        )

        logger.info(f"Context check: {estimated_total}/{self.max_context_length}")

        if estimated_total >= self.max_context_length:
            # Not enough room -- remove last assistant+user pair
            if message_history and message_history[-1].get("role") == "user":
                message_history.pop()
            if message_history and message_history[-1].get("role") == "assistant":
                message_history.pop()
            logger.info("Context limit reached, removed last assistant-user pair")
            return False, message_history

        return True, message_history

    def __repr__(self):
        return f"LLMClientBase(provider_class={self.provider_class}, model_name={self.model_name})"


# Backward compatible alias
LLMProviderClientBase = LLMClientBase
