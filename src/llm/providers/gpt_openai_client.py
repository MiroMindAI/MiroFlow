# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses
from typing import Any, Dict, List

from omegaconf import DictConfig
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from src.llm.provider_client_base import LLMProviderClientBase

from src.logging.logger import bootstrap_logger

import os

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
# OPENAI reasoning models only support temperature=1
OPENAI_REASONING_MODEL_SET = set(["o1", "o3", "o3-mini", "o4-mini", "gpt-5", "gpt-5-2025-08-07"])

logger = bootstrap_logger(level=LOGGER_LEVEL)


@dataclasses.dataclass
class GPTOpenAIClient(LLMProviderClientBase):
    def _create_client(self, config: DictConfig):
        """Create configured OpenAI client"""
        if self.async_client:
            return AsyncOpenAI(
                api_key=self.cfg.llm.openai_api_key,
                base_url=self.cfg.llm.openai_base_url,
                timeout=1800,
            )
        else:
            return OpenAI(
                api_key=self.cfg.llm.openai_api_key,
                base_url=self.cfg.llm.openai_base_url,
                timeout=1800,
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
        is_oai_new_model = (
            self.model_name.startswith("o1")
            or self.model_name.startswith("o3")
            or self.model_name.startswith("o4")
            or self.model_name.startswith("gpt-4.1")
            or self.model_name.startswith("gpt-4o")
            or self.model_name.startswith("gpt-5")
        )
        logger.debug(f" Calling LLM ({'async' if self.async_client else 'sync'})")
        # put the system prompt in the first message since OpenAI API does not support system prompt in
        if system_prompt:
            target_role = "developer" if is_oai_new_model else "system"

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
        )

        tool_list = await self.convert_tool_definition_to_tool_call(tools_definitions)

        try:
            # Set temperature and reasoning_effort for reasoning models
            if self.model_name in OPENAI_REASONING_MODEL_SET:
                temperature = 1.0
                params = {
                    "model": self.model_name,
                    "temperature": temperature,
                    "max_completion_tokens": self.max_tokens,
                    "messages": messages_copy,
                    "reasoning_effort": self.reasoning_effort,
                    "tools": tool_list,
                    "stream": False,
                }
            else:
                temperature = self.temperature
                params = {
                    "model": self.model_name,
                    "temperature": temperature,
                    "max_completion_tokens": self.max_tokens,
                    "messages": messages_copy,
                    "tools": tool_list,
                    "stream": False,
                }

            if self.top_p != 1.0:
                params["top_p"] = self.top_p
            # NOTE: min_p and top_k are not supported by OpenAI chat completion API, but SGLANG and VLLM support them
            if self.min_p != 0.0:
                params["min_p"] = self.min_p
            if self.top_k != -1:
                params["top_k"] = self.top_k

            if self.oai_tool_thinking:
                response = await self._handle_oai_tool_thinking(
                    params, messages, self.async_client
                )
            else:
                response = await self._create_completion(params, self.async_client)

            logger.debug(
                f"LLM call status: {getattr(response.choices[0], 'finish_reason', 'N/A')}"
            )
            return response
        except asyncio.CancelledError:
            logger.exception("[WARNING] LLM API call was cancelled during execution")
            raise
        except Exception as e:
            logger.exception(f"OpenAI LLM call failed: {str(e)}")
            raise e

    async def _create_completion(self, params: Dict[str, Any], is_async: bool):
        """Helper to create a completion, handling async and sync calls."""
        if is_async:
            return await self.client.chat.completions.create(**params)
        else:
            return self.client.chat.completions.create(**params)

    async def _handle_oai_tool_thinking(
        self, params: Dict[str, Any], messages: List[Dict[str, Any]], is_async: bool
    ):
        """Handles the logic for oai_tool_thinking."""
        # ---- Step 1: Let AI output text first, without calling tools ----
        params["tool_choice"] = "none"
        response = await self._create_completion(params, is_async)

        text_reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": text_reply})
        # We need a copy of messages for the second call.
        params["messages"] = messages

        # ---- Step 2: Allow tool_call ----
        del params["tool_choice"]
        response_tool = await self._create_completion(params, is_async)

        if response_tool.choices[0].finish_reason == "tool_calls":
            response_tool.choices[0].message.content = text_reply
            response = response_tool

        # ---- Step 3: Pop text_reply ----
        # Because the function outside will push response again
        messages.pop()
        return response

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
        elif llm_response.choices[0].finish_reason == "tool_calls":
            # For tool_calls, we need to extract tool call information as text
            tool_calls = llm_response.choices[0].message.tool_calls
            assistant_response_text = llm_response.choices[0].message.content or ""

            # If there's no text content, we generate a text describing the tool call
            if not assistant_response_text:
                tool_call_descriptions = []
                for tool_call in tool_calls:
                    tool_call_descriptions.append(
                        f"Using tool {tool_call.function.name} with arguments: {tool_call.function.arguments}"
                    )
                assistant_response_text = "\n".join(tool_call_descriptions)

            message_history.append(
                {
                    "role": "assistant",
                    "content": assistant_response_text,
                    "tool_calls": [
                        {
                            "id": _.id,
                            "type": "function",
                            "function": {
                                "name": _.function.name,
                                "arguments": _.function.arguments,
                            },
                        }
                        for _ in tool_calls
                    ],
                }
            )
        elif llm_response.choices[0].finish_reason == "length":
            assistant_response_text = llm_response.choices[0].message.content or ""
            if assistant_response_text == "":
                assistant_response_text = "LLM response is empty. This is likely due to thinking block used up all tokens."
            message_history.append(
                {"role": "assistant", "content": assistant_response_text}
            )
        else:
            raise ValueError(
                f"Unsupported finish reason: {llm_response.choices[0].finish_reason}"
            )
        logger.debug(f"LLM Response: {assistant_response_text}")

        return assistant_response_text, False

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """Extract tool call information from OpenAI LLM response"""
        from src.utils.parsing_utils import parse_llm_response_for_tool_calls

        # For OpenAI, get tool calls directly from response object
        if llm_response.choices[0].finish_reason == "tool_calls":
            return parse_llm_response_for_tool_calls(
                llm_response.choices[0].message.tool_calls
            )
        else:
            return [], []

    def update_message_history(
        self, message_history, tool_call_info, tool_calls_exceeded: bool = False
    ):
        """Update message history with tool calls data (llm client specific)"""

        for cur_call_id, tool_result in tool_call_info:
            message_history.append(
                {
                    "role": "tool",
                    "tool_call_id": cur_call_id,
                    "content": tool_result["text"],
                }
            )

        return message_history

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        """Handle max turns reached summary prompt"""
        return summary_prompt
