# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses
import os
from typing import Any, Dict, List

from omegaconf import DictConfig
from openai import AsyncOpenAI, DefaultAsyncHttpxClient, DefaultHttpxClient, OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from miroflow.llm.provider_client_base import LLMProviderClientBase
from miroflow.llm.providers.util import get_trace_id
from miroflow.logging.logger import bootstrap_logger
from miroflow.utils.prompt_utils import generate_no_mcp_system_prompt

# OPENAI reasoning models only support temperature=1
OPENAI_REASONING_MODEL_SET = set(["o1", "o3", "o3-mini", "o4-mini"])

logger = bootstrap_logger()


@dataclasses.dataclass
class GPTOpenAIResponseClient(LLMProviderClientBase):
    def _create_client(self, config: DictConfig):
        """Create configured OpenAI client"""
        http_client_args = {}
        trace_id = get_trace_id()
        if trace_id is not None:
            http_client_args["headers"] = {"trace-id": trace_id}
        if os.environ.get("HTTPS_PROXY"):
            http_client_args["proxy"] = os.environ.get("HTTPS_PROXY")
            logger.debug(f"Info: Using proxy {http_client_args['proxy']}")

        if self.async_client:
            return AsyncOpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=self.openai_base_url,
                http_client=DefaultAsyncHttpxClient(**http_client_args),
            )
        else:
            return OpenAI(
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=self.openai_base_url,
                http_client=DefaultHttpxClient(**http_client_args),
            )

    def _update_token_usage(self, usage_data):
        """Update cumulative token usage - OpenAI Response API implementation"""
        if usage_data:
            input_tokens = usage_data.get("input_tokens", 0)
            output_tokens = usage_data.get("output_tokens", 0)
            input_tokens_details = usage_data.get("input_tokens_details", None)
            if input_tokens_details:
                cached_tokens = input_tokens_details.get("cached_tokens", 0)
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
        """Format token usage statistics and cost estimation, returns summary_lines for format_final_summary and log string - OpenAI Response API implementation"""
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
        log_string = f"[OpenAI Response API/{self.model_name}] Total Input: {total_input}, Cache Input: {cache_input}, Output: {total_output}, Input Price: ${self.input_token_price:.4f} USD, Cache Input Price: ${self.cache_input_token_price:.4f} USD, Output Price: ${self.output_token_price:.4f} USD, Cost: ${cost:.4f} USD"

        return summary_lines, log_string

    @retry(wait=wait_fixed(10), stop=stop_after_attempt(5))
    async def _create_message(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_definitions,
        keep_tool_result: int = -1,
    ):
        """
        Send message to OpenAI Response API.
        :param system_prompt: System prompt string.
        :param messages: Message history list.
        :return: OpenAI API response object or None (if error).
        """
        logger.debug(
            f" Calling LLM Response API ({'async' if self.async_client else 'sync'})"
        )

        # Build Response API input format
        # Response API uses different input format, need to convert messages to text
        conversation_text = self._convert_messages_to_text(system_prompt, messages)
        tool_list = await self.convert_tool_definition_to_tool_call(tools_definitions)

        try:
            # Set temperature=1 for reasoning models
            temperature = (
                1.0
                if self.model_name in OPENAI_REASONING_MODEL_SET
                else self.temperature
            )

            params = {
                "model": self.model_name,
                "reasoning": {"effort": "high", "summary": "auto"},
                "temperature": temperature,
                "input": conversation_text,
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

            response = await self._create_response(params, self.async_client)

            response = response.to_dict()
            # Convert response to a serializable format to avoid JSON serialization issues
            response = self._convert_response_to_serializable(response)

            # Update token count
            self._update_token_usage(response.get("usage", None))
            logger.debug(
                f"LLM Response API call status: {response.get('error', 'N/A')}"
            )
            return response
        except asyncio.CancelledError:
            logger.debug(
                "[WARNING] LLM Response API call was cancelled during execution"
            )
            raise
        except Exception as e:
            logger.debug(f"OpenAI Response API LLM call failed: {str(e)}")
            raise e

    def _convert_messages_to_text(
        self, system_prompt: str, messages: List[Dict[str, Any]]
    ) -> str:
        """Convert message list to text format required by Response API"""
        conversation_parts = []

        # Add system prompt
        if system_prompt:
            conversation_parts.append(f"System: {system_prompt}")

        # Convert messages
        for message in messages:
            role = message.get("role", "")
            content = message.get("content", "")

            if role == "user":
                if isinstance(content, list):
                    # Handle multimodal content
                    text_content = []
                    for item in content:
                        if item.get("type") == "text":
                            text_content.append(item.get("text", ""))
                    conversation_parts.append(f"User: {' '.join(text_content)}")
                else:
                    conversation_parts.append(f"User: {content}")
            elif role == "assistant":
                conversation_parts.append(f"Assistant: {content}")
            elif role == "tool":
                tool_call_id = message.get("tool_call_id", "")
                tool_content = message.get("content", "")
                conversation_parts.append(
                    f"Tool Result (ID: {tool_call_id}): {tool_content}"
                )

        return "\n\n".join(conversation_parts)

    async def _create_response(self, params: Dict[str, Any], is_async: bool):
        """Helper to create a response using OpenAI's Response API."""
        if is_async:
            return await self.client.responses.create(**params)
        else:
            return self.client.responses.create(**params)

    @staticmethod
    async def convert_tool_definition_to_tool_call(tools_definitions):
        tool_list = []
        for server in tools_definitions:
            if "tools" in server and len(server["tools"]) > 0:
                for tool in server["tools"]:
                    tool_def = dict(
                        type="function",
                        name=f"{server['name']}-{tool['name']}",
                        description=tool["description"],
                        parameters=tool["schema"],
                    )
                    tool_list.append(tool_def)
        return tool_list

    def process_llm_response(
        self, llm_response, message_history, agent_type="main"
    ) -> tuple[str, bool]:
        """Process OpenAI Response API LLM response"""
        if not llm_response:
            error_msg = "LLM did not return a valid response."
            logger.debug(f"Error: {error_msg}")
            return "", True  # Exit loop

        # Now working with serializable response format
        assistant_response_text = ""
        response_output = llm_response.get("output", None)

        reasoning_text = ""
        message_text = ""
        tool_call_descriptions = []
        tool_call_list = []

        if response_output and isinstance(response_output, list):
            for item in response_output:
                if item.get("type") == "reasoning":
                    for summary_item in item["summary"]:
                        if summary_item.get("type") == "summary_text":
                            reasoning_text += summary_item.get("text", "")

                if item.get("type") == "message":
                    for content_item in item["content"]:
                        if content_item.get("type") == "output_text":
                            message_text += content_item.get("text", "")

                if item.get("type") == "function_call":
                    tool_call_descriptions.append(
                        f"Using tool {item.get('name')} with arguments: {item.get('arguments')}"
                    )
                    tool_call_list.append(
                        {
                            "id": item.get("call_id"),
                            "type": "function",
                            "function": {
                                "name": item.get("name"),
                                "arguments": item.get("arguments"),
                            },
                        }
                    )
        if reasoning_text:
            reasoning_text = "<think>\n" + reasoning_text + "\n</think>\n\n"
        assistant_response_text = reasoning_text + message_text

        # If both reasoning_text and message_text are empty, use tool_call_descriptions
        if not assistant_response_text:
            assistant_response_text = "\n".join(tool_call_descriptions)

        message_item = {
            "role": "assistant",
            "content": assistant_response_text,
        }
        if tool_call_list:
            message_item["tool_calls"] = tool_call_list

        message_history.append(message_item)

        logger.debug(f"LLM Response: {assistant_response_text}")

        return assistant_response_text, False

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """Extract tool call information from OpenAI Response API LLM response"""
        from miroflow.utils.parsing_utils import parse_llm_response_for_tool_calls

        return parse_llm_response_for_tool_calls(llm_response)

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
        return generate_no_mcp_system_prompt(date)

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        """Handle max turns reached summary prompt"""
        return summary_prompt

    def get_token_usage(self):
        """Get current cumulative token usage - OpenAI Response API implementation"""
        return self.token_usage.copy()

    def _convert_response_to_serializable(self, response):
        """Convert Response API response to a serializable format"""
        if not response:
            raise ValueError("not possible to serialize")

        # Create a simple dict structure that can be serialized
        serializable_response = {
            "type": "openai_response",
            "output": response.get("output", ""),
            "usage": response.get("usage", None),
        }

        return serializable_response
