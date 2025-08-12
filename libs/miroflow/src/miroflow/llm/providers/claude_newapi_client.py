# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# -*- coding: utf-8 -*-
"""
author: lei.lei@shanda.com
time: 2025/07/10 11:46
description: anthropic client via New API server.
NewAPI is like litellm/openrouter, all LLM uses openAI endpoint.
see NewAPI documentation here:
"""

import asyncio
import dataclasses

# from tenacity import retry, stop_after_attempt, wait_fixed
import json
from typing import Any, Dict, List

from omegaconf import DictConfig, OmegaConf
from openai import AsyncOpenAI, DefaultAsyncHttpxClient, DefaultHttpxClient, OpenAI

from miroflow.llm.provider_client_base import LLMProviderClientBase
from miroflow.llm.providers.util import get_trace_id
from miroflow.logging.logger import bootstrap_logger
from miroflow.utils.prompt_utils import generate_mcp_system_prompt

logger = bootstrap_logger()


@dataclasses.dataclass
class ClaudeNewAPIClient(LLMProviderClientBase):
    def _create_client(self, config: DictConfig):
        http_client_args = {}
        if (trace_id := get_trace_id()) is not None:
            http_client_args["headers"] = {"trace-id": trace_id}
        if not OmegaConf.is_missing(config.env, "https_proxy"):
            http_client_args["proxy"] = config.env.https_proxy

        logger.debug(f"http_client_args {http_client_args['proxy']}")

        if self.async_client:
            return AsyncOpenAI(
                api_key=config.env.newapi_api_key,
                base_url=config.env.newapi_base_url,
                http_client=DefaultAsyncHttpxClient(**http_client_args),
            )
        else:
            return OpenAI(
                api_key=config.env.newapi_api_key,
                base_url=config.env.newapi_base_url,
                http_client=DefaultHttpxClient(**http_client_args),
            )

    def _update_token_usage(self, usage_data):
        """Update cumulative token usage - OpenAI implementation"""
        if usage_data:
            input_tokens = getattr(usage_data, "prompt_tokens", 0)
            output_tokens = getattr(usage_data, "completion_tokens", 0)
            prompt_tokens_details = getattr(usage_data, "prompt_tokens_details", None)
            if prompt_tokens_details:
                cached_tokens = getattr(prompt_tokens_details, "cached_tokens", 0)
            else:
                cached_tokens = 0
            # OpenAI does not provide cache_creation_input_tokens
            self.token_usage["total_input_tokens"] += input_tokens
            self.token_usage["total_output_tokens"] += output_tokens
            self.token_usage["total_cache_read_input_tokens"] += cached_tokens

            logger.debug(
                f"Current round token usage - Input: {self.token_usage['total_input_tokens']}, "
                f"Output: {self.token_usage['total_output_tokens']}"
            )

    def format_token_usage_summary(self):
        """Format token usage statistics and cost estimation, returns summary_lines for format_final_summary and log string - OpenAI implementation"""
        token_usage = self.get_token_usage()

        total_input = token_usage.get("total_input_tokens", 0)
        total_output = token_usage.get("total_output_tokens", 0)
        cache_input = token_usage.get("total_cache_input_tokens", 0)

        # Actual cost (considering cache)
        cost = (
            ((total_input - cache_input) / 1_000_000 * self.input_token_price)
            + (cache_input / 1_000_000 * self.cache_input_token_price)
            + (total_output / 1_000_000 * self.output_token_price)
        )

        summary_lines = []
        summary_lines.append("\n" + "-" * 20 + " Token Usage & Cost " + "-" * 20)
        summary_lines.append(f"Total Input Tokens: {total_input}")
        summary_lines.append(f"Total Cache Input Tokens: {cache_input}")
        summary_lines.append(f"Total Output Tokens: {total_output}")
        summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))
        summary_lines.append(f"Input Token Price: ${self.input_token_price:.4f} USD")
        summary_lines.append(f"Output Token Price: ${self.output_token_price:.4f} USD")
        summary_lines.append(
            f"Cache Input Token Price: ${self.cache_input_token_price:.4f} USD"
        )
        summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))
        summary_lines.append(f"Estimated Cost (with cache): ${cost:.4f} USD")
        summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))

        # Generate log string
        log_string = f"[OpenAI/{self.model_name}] Total Input: {total_input}, Cache Input: {cache_input}, Output: {total_output}, Input Price: ${self.input_token_price:.4f} USD, Cache Input Price: ${self.cache_input_token_price:.4f} USD, Output Price: ${self.output_token_price:.4f} USD, Cost: ${cost:.4f} USD"

        return summary_lines, log_string

    # @retry(wait=wait_fixed(10), stop=stop_after_attempt(5))
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
        TODO: test claude with this
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

        tool_list = await self.convert_tool_definition_to_tool_call(tools_definitions)

        params = None
        try:
            temperature = self.temperature

            params = {
                "model": self.model_name,
                "temperature": temperature,
                "top_p": self.top_p if self.top_p != 1.0 else None,
                # anthropic_newapi_client.py:180 - OpenAI LLM call failed: Error code: 400 - {'error': {'message': '{"message":"max_completion_tokens: Extra inputs are not permitted"} (request id: 20250710142205168231272cF2KaQpL) (request id: 2025071014220578275572hVfJquBZ)', 'type': 'upstream_error', 'param': '400', 'code': 'bad_response_status_code'}}
                # "max_completion_tokens": self.max_tokens,
                "max_tokens": self.max_tokens,
                "messages": messages_copy,
                "tools": tool_list,
                "stream": False,
            }

            response = await self._create_completion(params, self.async_client)

            # Update token count
            self._update_token_usage(getattr(response, "usage", None))
            logger.debug(
                f"LLM call status: {getattr(response.choices[0], 'finish_reason', 'N/A')}"
            )
            return response
        except asyncio.CancelledError:
            logger.debug("[WARNING] LLM API call was cancelled during execution")
            raise
        except Exception as e:
            logger.error(
                f"OpenAI LLM call failed: {str(e)}, input = {json.dumps(params)}",
                exc_info=True,
            )
            raise e

    async def _create_completion(self, params: Dict[str, Any], is_async: bool):
        """Helper to create a completion, handling async and sync calls."""
        if is_async:
            return await self.client.chat.completions.create(**params)
        else:
            return self.client.chat.completions.create(**params)

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
        from miroflow.utils.parsing_utils import parse_llm_response_for_tool_calls

        # For OpenAI, directly get tool calls from response object
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

    def generate_agent_system_prompt(self, date, mcp_servers) -> str:
        return generate_mcp_system_prompt(date, mcp_servers)

    def parse_llm_response(self, llm_response) -> str:
        """Parse OpenAI LLM response to get text content"""
        if not llm_response or not llm_response.choices:
            raise ValueError("LLM did not return a valid response.")
        return llm_response.choices[0].message.content

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        """Handle max turns reached summary prompt"""
        return summary_prompt

    def get_token_usage(self):
        """Get current cumulative token usage - OpenAI implementation"""
        return self.token_usage.copy()
