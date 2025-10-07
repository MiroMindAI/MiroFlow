# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses
import json
import os
import re
from typing import Any, Dict, List

import tiktoken
from omegaconf import DictConfig
from openai import AsyncOpenAI, OpenAI
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.llm.provider_client_base import LLMProviderClientBase

from src.logging.logger import bootstrap_logger

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


class ContextLimitError(Exception):
    pass


@dataclasses.dataclass
class ClaudeOpenRouterClient(LLMProviderClientBase):
    def _create_client(self, config: DictConfig):
        """Create configured OpenAI client"""
        if self.async_client:
            return AsyncOpenAI(
                api_key=self.cfg.llm.openrouter_api_key,
                base_url=self.cfg.llm.openrouter_base_url,
                timeout=1800,
            )
        else:
            return OpenAI(
                api_key=self.cfg.llm.openrouter_api_key,
                base_url=self.cfg.llm.openrouter_base_url,
                timeout=1800,
            )

    @retry(
        wait=wait_exponential(multiplier=5),
        stop=stop_after_attempt(5),
        retry=retry_if_not_exception_type(ContextLimitError),
    )
    async def _create_message(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_definitions,
        keep_tool_result: int = -1,
    ):
        """
        Send message to OpenAI API.
        :param system_prompt: System prompt string.
        :param messages: Message history list.
        :return: OpenAI API response object or None (if error).
        """
        logger.debug(f" Calling LLM ({'async' if self.async_client else 'sync'})")
        # put the system prompt in the first message since OpenAI API does not support system prompt in
        if system_prompt:
            target_role = "system"

            # Check if there are already system or developer messages
            if messages and messages[0]["role"] in ["system", "developer"]:
                # Replace existing message with correct role
                messages[0] = {
                    "role": target_role,
                    "content": [dict(type="text", text=system_prompt)],
                }
            else:
                # Insert new message
                messages.insert(
                    0,
                    {
                        "role": target_role,
                        "content": [dict(type="text", text=system_prompt)],
                    },
                )

        messages_copy = self._remove_tool_result_from_messages(
            messages, keep_tool_result
        )

        # Apply cache control
        if self.disable_cache_control:
            processed_messages = messages_copy
        else:
            processed_messages = self._apply_cache_control(messages_copy)

        params = None
        try:
            temperature = self.temperature

            # build extra_body if self.openrouter_provider
            provider_config = (self.openrouter_provider or "").strip().lower()
            logger.info(f"provider_config: {provider_config}")
            if provider_config == "google":
                extra_body = {
                    "provider": {
                        "only": [
                            "google-vertex/us",
                            "google-vertex/europe",
                            "google-vertex/global",
                        ]
                    }
                }
            elif provider_config == "anthropic":
                extra_body = {"provider": {"only": ["anthropic"]}}
                # extra_body["provider"]["ignore"] = ["google-vertex/us", "google-vertex/europe", "google-vertex/global"]
            elif provider_config == "amazon":
                extra_body = {"provider": {"only": ["amazon-bedrock"]}}
            elif provider_config != "":
                extra_body = {"provider": {"only": [provider_config]}}
            else:
                extra_body = {}

            # Add top_k and min_p through extra_body for OpenRouter
            if self.top_k != -1:
                extra_body["top_k"] = self.top_k
            if self.min_p != 0.0:
                extra_body["min_p"] = self.min_p
            if self.repetition_penalty != 1.0:
                extra_body["repetition_penalty"] = self.repetition_penalty

            params = {
                "model": self.model_name,
                "temperature": temperature,
                "max_tokens": self.max_tokens,
                "messages": processed_messages,
                "stream": False,
                "extra_body": extra_body,
            }

            # Add optional parameters only if they have non-default values
            if self.top_p != 1.0:
                params["top_p"] = self.top_p

            response = await self._create_completion(params, self.async_client)

            if (
                response is None
                or response.choices is None
                or len(response.choices) == 0
            ):
                logger.debug(f"LLM call failed: response = {response}")
                raise Exception(f"LLM call failed [rare case]: response = {response}")

            if response.choices and response.choices[0].finish_reason == "length":
                logger.debug(
                    "LLM finish_reason is 'length', triggering ContextLimitError"
                )
                raise ContextLimitError(
                    "(finish_reason=length) Response truncated due to maximum context length"
                )

            if (
                response.choices
                and response.choices[0].finish_reason == "stop"
                and response.choices[0].message.content.strip() == ""
            ):
                logger.debug(
                    "LLM finish_reason is 'stop', but content is empty, triggering Error"
                )
                raise Exception("LLM finish_reason is 'stop', but content is empty")

            logger.debug(
                f"LLM call finish_reason: {getattr(response.choices[0], 'finish_reason', 'N/A')}"
            )
            return response
        except asyncio.CancelledError:
            logger.debug("[WARNING] LLM API call was cancelled during execution")
            raise Exception("LLM API call was cancelled during execution")
        except Exception as e:
            error_str = str(e)
            if (
                "Input is too long for requested model" in error_str
                or "input length and `max_tokens` exceed context limit" in error_str
                or "maximum context length" in error_str
                or "prompt is too long" in error_str
                or "exceeds the maximum length" in error_str
                or "exceeds the maximum allowed length" in error_str
                or "Input tokens exceed the configured limit" in error_str
                or "Requested token count exceeds the model's maximum context length"
                in error_str
                or "BadRequestError" in error_str
                and "context length" in error_str
            ):
                logger.debug(f"OpenRouter LLM Context limit exceeded: {error_str}")
                raise ContextLimitError(f"Context limit exceeded: {error_str}")

            logger.error(
                f"OpenRouter LLM call failed: {str(e)}, input = {json.dumps(params)}",
                exc_info=True,
            )
            raise e

    async def _create_completion(self, params: Dict[str, Any], is_async: bool):
        """Helper to create a completion, handling async and sync calls."""
        if is_async:
            return await self.client.chat.completions.create(**params)
        else:
            return self.client.chat.completions.create(**params)

    def _clean_user_content_from_response(self, text: str) -> str:
        """Remove content between \\n\\nUser: and <use_mcp_tool> in assistant response (if no <use_mcp_tool>, remove to end)"""
        # Match content between \n\nUser: and <use_mcp_tool>, if no <use_mcp_tool> delete to text end
        pattern = r"\n\nUser:.*?(?=<use_mcp_tool>|$)"
        cleaned_text = re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)

        return cleaned_text

    def process_llm_response(
        self, llm_response, message_history, agent_type="main"
    ) -> tuple[str, bool]:
        """Process OpenAI LLM response"""

        if not llm_response or not llm_response.choices:
            error_msg = "LLM did not return a valid response."
            logger.error(f"Should never happen: {error_msg}")
            return "", True  # Exit loop

        # Extract LLM response text
        if llm_response.choices[0].finish_reason == "stop":
            assistant_response_text = llm_response.choices[0].message.content or ""
            # remove user: {...} content
            assistant_response_text = self._clean_user_content_from_response(
                assistant_response_text
            )
            message_history.append(
                {"role": "assistant", "content": assistant_response_text}
            )
        elif llm_response.choices[0].finish_reason == "length":
            assistant_response_text = llm_response.choices[0].message.content or ""
            if assistant_response_text == "":
                assistant_response_text = "LLM response is empty. This is likely due to thinking block used up all tokens."
            else:
                assistant_response_text = self._clean_user_content_from_response(
                    assistant_response_text
                )
            message_history.append(
                {"role": "assistant", "content": assistant_response_text}
            )
        else:
            logger.error(
                f"Unsupported finish reason: {llm_response.choices[0].finish_reason}"
            )
            assistant_response_text = (
                "Successful response, but unsupported finish reason: "
                + llm_response.choices[0].finish_reason
            )
            message_history.append(
                {"role": "assistant", "content": assistant_response_text}
            )
        logger.debug(f"LLM Response: {assistant_response_text}")

        return assistant_response_text, False

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """Extract tool call information from OpenAI LLM response"""
        from src.utils.parsing_utils import parse_llm_response_for_tool_calls

        # For Anthropic, parse tool calls from response text
        return parse_llm_response_for_tool_calls(assistant_response_text)

    def update_message_history(
        self, message_history, tool_call_info, tool_calls_exceeded=False
    ):
        """Update message history with tool calls data (llm client specific)"""

        # Filter tool call results with type "text"
        tool_call_info = [item for item in tool_call_info if item[1]["type"] == "text"]

        # Separate valid tool calls and bad tool calls
        valid_tool_calls = [
            (tool_id, content)
            for tool_id, content in tool_call_info
            if tool_id != "FAILED"
        ]
        bad_tool_calls = [
            (tool_id, content)
            for tool_id, content in tool_call_info
            if tool_id == "FAILED"
        ]

        total_calls = len(valid_tool_calls) + len(bad_tool_calls)

        # Build output text
        output_parts = []

        if total_calls > 1:
            # Handling for multiple tool calls
            # Add tool result description
            if tool_calls_exceeded:
                output_parts.append(
                    f"You made too many tool calls. I can only afford to process {len(valid_tool_calls)} valid tool calls in this turn."
                )
            else:
                output_parts.append(
                    f"I have processed {len(valid_tool_calls)} valid tool calls in this turn."
                )

            # Output each valid tool call result according to format
            for i, (tool_id, content) in enumerate(valid_tool_calls, 1):
                output_parts.append(f"Valid tool call {i} result:\n{content['text']}")

            # Output bad tool calls results
            for i, (tool_id, content) in enumerate(bad_tool_calls, 1):
                output_parts.append(f"Failed tool call {i} result:\n{content['text']}")
        else:
            # For single tool call, output result directly
            for tool_id, content in valid_tool_calls:
                output_parts.append(content["text"])
            for tool_id, content in bad_tool_calls:
                output_parts.append(content["text"])

        merged_text = "\n\n".join(output_parts)

        message_history.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": merged_text}],
            }
        )
        return message_history

    def parse_llm_response(self, llm_response) -> str:
        """Parse OpenAI LLM response to get text content"""
        if not llm_response or not llm_response.choices:
            raise ValueError("LLM did not return a valid response.")
        return llm_response.choices[0].message.content

    def _estimate_tokens(self, text: str) -> int:
        """Use tiktoken to estimate token count of text"""
        if not hasattr(self, "encoding"):
            # Initialize tiktoken encoder
            try:
                self.encoding = tiktoken.get_encoding("o200k_base")
            except Exception:
                # If o200k_base is not available, use cl100k_base as fallback
                self.encoding = tiktoken.get_encoding("cl100k_base")

        try:
            return len(self.encoding.encode(text))
        except Exception:
            # If encoding fails, use simple estimation: about 1 token per 4 characters
            return len(text) // 4

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        """Handle max turns reached summary prompt"""
        if message_history[-1]["role"] == "user":
            last_user_message = message_history.pop()
            return (
                last_user_message["content"][0]["text"]
                + "\n\n-----------------\n\n"
                + summary_prompt
            )
        else:
            return summary_prompt

    def _apply_cache_control(self, messages):
        """Apply cache control to the last user message and system message (if applicable)"""
        cached_messages = []
        user_turns_processed = 0
        for turn in reversed(messages):
            if (turn["role"] == "user" and user_turns_processed < 1) or (
                turn["role"] == "system"
            ):
                # Add ephemeral cache control to the text part of the last user message
                new_content = []
                processed_text = False
                # Check if content is a list
                if isinstance(turn.get("content"), list):
                    # see example here
                    # https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching
                    for item in turn["content"]:
                        if (
                            item.get("type") == "text"
                            and len(item.get("text")) > 0
                            and not processed_text
                        ):
                            # Copy and add cache control
                            text_item = item.copy()
                            text_item["cache_control"] = {"type": "ephemeral"}
                            new_content.append(text_item)
                            processed_text = True
                        else:
                            # Other types of content (like image) copy directly
                            new_content.append(item.copy())
                    cached_messages.append(
                        {"role": turn["role"], "content": new_content}
                    )
                else:
                    # If content is not a list (e.g., plain text), add as is without cache control
                    # Or adjust logic as needed
                    logger.debug(
                        "Warning: User message content is not in expected list format, cache control not applied."
                    )
                    cached_messages.append(turn)
                user_turns_processed += 1
            else:
                # Other messages add directly
                cached_messages.append(turn)
        return list(reversed(cached_messages))
