# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses
import os

from anthropic import (
    NOT_GIVEN,
    Anthropic,
    AsyncAnthropic,
)
from omegaconf import DictConfig
from tenacity import retry, stop_after_attempt, wait_fixed

from src.llm.provider_client_base import LLMProviderClientBase

from src.logging.logger import bootstrap_logger

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


@dataclasses.dataclass
class ClaudeAnthropicClient(LLMProviderClientBase):
    def __post_init__(self):
        super().__post_init__()

    def _create_client(self, config: DictConfig):
        """Create Anthropic client"""
        api_key = self.cfg.llm.anthropic_api_key

        if self.async_client:
            return AsyncAnthropic(
                api_key=api_key,
                base_url=self.cfg.llm.anthropic_base_url,
                timeout=600.0,  # 10 minutes timeout for long requests
            )
        else:
            return Anthropic(
                api_key=api_key,
                base_url=self.cfg.llm.anthropic_base_url,
                timeout=600.0,  # 10 minutes timeout for long requests
            )

    @retry(wait=wait_fixed(10), stop=stop_after_attempt(5))
    async def _create_message(
        self,
        system_prompt,
        messages,
        tools_definitions,
        keep_tool_result: int = -1,
    ):
        """
        Send message to Anthropic API.
        :param system_prompt: System prompt string.
        :param messages: Message history list.
        :return: Anthropic API response object or None (if error).
        """
        logger.debug(f" Calling LLM ({'async' if self.async_client else 'sync'})")

        messages_copy = self._remove_tool_result_from_messages(
            messages, keep_tool_result
        )

        processed_messages = self._apply_cache_control(messages_copy)

        try:
            if self.async_client:
                response = await self.client.messages.create(
                    model=self.model_name,
                    temperature=self.temperature,
                    top_p=self.top_p if self.top_p != 1.0 else NOT_GIVEN,
                    top_k=self.top_k if self.top_k != -1 else NOT_GIVEN,
                    max_tokens=self.max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=processed_messages,
                    stream=False,
                )
            else:
                response = self.client.messages.create(
                    model=self.model_name,
                    temperature=self.temperature,
                    top_p=self.top_p if self.top_p != 1.0 else NOT_GIVEN,
                    top_k=self.top_k if self.top_k != -1 else NOT_GIVEN,
                    max_tokens=self.max_tokens,
                    system=[
                        {
                            "type": "text",
                            "text": system_prompt,
                            "cache_control": {"type": "ephemeral"},
                        }
                    ],
                    messages=processed_messages,
                    stream=False,
                )
            logger.debug(f"LLM call status: {getattr(response, 'stop_reason', 'N/A')}")
            return response
        except asyncio.CancelledError:
            logger.exception("[WARNING] LLM API call was cancelled during execution")
            raise  # Re-raise to allow decorator to log it
        except Exception as e:
            logger.exception("Anthropic LLM endpoint failed")
            raise e

    def process_llm_response(
        self, llm_response, message_history, agent_type="main"
    ) -> tuple[str, bool]:
        """Process Anthropic LLM response"""
        if not llm_response:
            logger.debug("[ERROR] LLM call failed, skipping this response.")
            return "", True

        if not hasattr(llm_response, "content") or not llm_response.content:
            logger.debug("[ERROR] LLM response is empty or doesn't contain content.")
            return "", True

        # Extract response content
        assistant_response_text = ""
        assistant_response_content = []

        for block in llm_response.content:
            if block.type == "text":
                assistant_response_text += block.text + "\n"
                assistant_response_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                assistant_response_content.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )

        message_history.append(
            {"role": "assistant", "content": assistant_response_content}
        )

        logger.debug(f"LLM Response: {assistant_response_text}")

        return assistant_response_text, False

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """Extract tool call information from Anthropic LLM response"""
        from src.utils.parsing_utils import parse_llm_response_for_tool_calls

        # For Anthropic, parse tool calls from the response text
        return parse_llm_response_for_tool_calls(assistant_response_text)

    def update_message_history(
        self, message_history, tool_call_info, tool_calls_exceeded: bool = False
    ):
        """Update message history with tool calls data (llm client specific)"""

        merged_text = "\n".join(
            [item[1]["text"] for item in tool_call_info if item[1]["type"] == "text"]
        )

        message_history.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": merged_text}],
            }
        )

        return message_history

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        """Handle max turns reached summary prompt"""
        if message_history[-1]["role"] == "user":
            last_user_message = message_history.pop()
            return (
                last_user_message["content"][0]["text"]
                + "\n*************\n"
                + summary_prompt
            )
        else:
            return summary_prompt

    def _extract_usage_from_response(self, response):
        """Extract usage - Anthropic format"""
        if not hasattr(response, "usage"):
            return {
                "input_tokens": 0,
                "cached_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
            }

        usage = response.usage
        cache_creation_input_tokens = getattr(usage, "cache_creation_input_tokens", 0)
        cache_read_input_tokens = getattr(usage, "cache_read_input_tokens", 0)
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)

        usage_dict = {
            "input_tokens": cache_creation_input_tokens
            + cache_read_input_tokens
            + input_tokens,
            "cached_tokens": cache_read_input_tokens,
            "output_tokens": output_tokens,
            "reasoning_tokens": 0,
        }

        return usage_dict

    def _apply_cache_control(self, messages):
        """Apply cache control to the last user message and system message (if applicable)"""
        cached_messages = []
        user_turns_processed = 0
        for turn in reversed(messages):
            if turn["role"] == "user" and user_turns_processed < 1:
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
                            # Other types of content (like image) copied directly
                            new_content.append(item.copy())
                    cached_messages.append({"role": "user", "content": new_content})
                else:
                    # If content is not a list (e.g., plain text), add as is without cache control
                    # Or adjust logic as needed
                    logger.debug(
                        "Warning: User message content is not in expected list format, cache control not applied."
                    )
                    cached_messages.append(turn)

                user_turns_processed += 1
            else:
                # Add other messages directly
                cached_messages.append(turn)
        return list(reversed(cached_messages))
