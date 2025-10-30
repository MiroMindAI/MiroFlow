# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import dataclasses
from typing import Any, Dict, List

from omegaconf import DictConfig
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from src.llm.provider_client_base import LLMProviderClientBase

from src.logging.logger import bootstrap_logger

import os

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


@dataclasses.dataclass
class QwenSGLangClient(LLMProviderClientBase):
    def _create_client(self, config: DictConfig):
        """Create configured OpenAI client"""
        if self.async_client:
            return AsyncOpenAI(
                api_key=config.env.qwen_api_key,
                base_url=config.env.qwen_base_url,
            )
        else:
            return OpenAI(
                api_key=config.env.qwen_api_key,
                base_url=config.env.qwen_base_url,
            )

    @retry(wait=wait_fixed(10), stop=stop_after_attempt(5))
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
        :return: OpenAI API response object or None (if error occurs).
        """

        logger.debug(f" Calling LLM ({'async' if self.async_client else 'sync'})")
        # put the system prompt in the first message since OpenAI API does not support system prompt in
        if system_prompt:
            target_role = "system"

            # Check if there's already a system or developer message
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
        )  # if keep_tool_result=-1, do nothing

        params = {
            "model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "messages": messages_copy,
            "tools": [],
            "stream": False,
        }

        if self.top_p != 1.0:
            params["top_p"] = self.top_p
        # NOTE: min_p and top_k are not supported by OpenAI chat completion API, but SGLANG and VLLM support them
        if self.min_p != 0.0:
            params["min_p"] = self.min_p
        if self.top_k != -1:
            params["top_k"] = self.top_k

        try:
            if self.async_client:
                response = await self.client.chat.completions.create(**params)
            else:
                response = self.client.chat.completions.create(**params)

            logger.debug(
                f"LLM call status: {getattr(response.choices[0], 'finish_reason', 'N/A')}"
            )
            return response
        except Exception as e:
            logger.debug(f"OpenAI LLM call failed: {str(e)}")
            raise e

    def process_llm_response(
        self, llm_response, message_history, agent_type="main"
    ) -> tuple[str, bool]:
        """Process OpenAI LLM response"""
        if not llm_response or not llm_response.choices:
            error_msg = "LLM did not return a valid response."
            logger.debug(f"Error: {error_msg}")
            return "", True  # Exit loop

        # Extract LLM response text
        if llm_response.choices[0].finish_reason == "stop":
            assistant_response_text = llm_response.choices[0].message.content or ""
            message_history.append(
                {"role": "assistant", "content": assistant_response_text}
            )
        elif llm_response.choices[0].finish_reason == "length":
            assistant_response_text = llm_response.choices[0].message.content or ""
            if assistant_response_text == "":
                assistant_response_text = "LLM response is empty. This is likely due to thinking block used up all tokens."
            message_history.append(
                {"role": "assistant", "content": assistant_response_text}
            )
        else:
            # Different from Openai Client, we don't use tool calls for qwen,
            # so we don't support tool_call finish reason
            raise ValueError(
                f"Unsupported finish reason: {llm_response.choices[0].finish_reason}"
            )
        logger.debug(f"LLM Response: {assistant_response_text}")

        return assistant_response_text, False

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """Extract tool call information from Qwen LLM response"""
        from ...utils.parsing_utils import parse_llm_response_for_tool_calls

        # For qwen, use the same parsing method as anthropic
        return parse_llm_response_for_tool_calls(assistant_response_text)

    def update_message_history(
        self, message_history, tool_call_info, tool_calls_exceeded=False
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
