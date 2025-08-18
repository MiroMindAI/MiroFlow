# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses

from anthropic import (
    NOT_GIVEN,
    Anthropic,
    AsyncAnthropic,
    DefaultAsyncHttpxClient,
    DefaultHttpxClient,
)
from omegaconf import DictConfig
from tenacity import retry, stop_after_attempt, wait_fixed

from miroflow.llm.provider_client_base import LLMProviderClientBase
from miroflow.llm.providers.util import get_trace_id
from miroflow.logging.logger import bootstrap_logger
from miroflow.utils.prompt_utils import generate_mcp_system_prompt

logger = bootstrap_logger()


@dataclasses.dataclass
class ClaudeAnthropicClient(LLMProviderClientBase):
    def __post_init__(self):
        super().__post_init__()

        # Anthropic specific token counter
        self.input_tokens: int = 0
        self.output_tokens: int = 0
        self.cache_creation_tokens: int = 0
        self.cache_read_tokens: int = 0

    def _create_client(self, config: DictConfig):
        """Create Anthropic client"""
        api_key = config.env.anthropic_api_key
        http_client_args = {}
        trace_id = get_trace_id()
        if trace_id is not None:
            http_client_args["headers"] = {"trace-id": trace_id}
        if (proxy := config.get("env.https_proxy", "???")) != "???":
            http_client_args["proxy"] = proxy
            logger.debug(f"Info: Using proxy {http_client_args['proxy']}")

        if self.async_client:
            return AsyncAnthropic(
                api_key=api_key,
                base_url=self.anthropic_base_url,
                http_client=DefaultAsyncHttpxClient(**http_client_args),
            )
        else:
            return Anthropic(
                api_key=api_key,
                base_url=self.anthropic_base_url,
                http_client=DefaultHttpxClient(**http_client_args),
            )

    def _update_token_usage(self, usage_data):
        """Update cumulative token usage - Anthropic implementation"""
        if usage_data:
            # Update based on actual field names returned by the Anthropic API
            self.token_usage["total_cache_write_input_tokens"] += (
                getattr(usage_data, "cache_creation_input_tokens", 0) or 0
            )
            self.token_usage["total_cache_read_input_tokens"] += (
                getattr(usage_data, "cache_read_input_tokens", 0) or 0
            )
            self.token_usage["total_input_tokens"] += (
                getattr(usage_data, "input_tokens", 0) or 0
            )
            self.token_usage["total_output_tokens"] += (
                getattr(usage_data, "output_tokens", 0) or 0
            )
            logger.debug(
                f"This round Token usage - Input: {getattr(usage_data, 'input_tokens', 0)}, "
                f"Cache creation input: {getattr(usage_data, 'cache_creation_input_tokens', 0)}, "
                f"Cache read input: {getattr(usage_data, 'cache_read_input_tokens', 0)}, "
                f"Output: {getattr(usage_data, 'output_tokens', 0)}"
            )
        else:
            logger.debug("Warning: Did not receive valid usage_data.")

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
            # update token count

            self._update_token_usage(getattr(response, "usage", None))
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
        from miroflow.utils.parsing_utils import parse_llm_response_for_tool_calls

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

    def generate_agent_system_prompt(self, date, mcp_servers) -> str:
        return generate_mcp_system_prompt(date, mcp_servers)

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

    def format_token_usage_summary(self):
        """Format token usage statistics and cost estimation, return summary_lines for format_final_summary and log string - Anthropic implementation"""
        token_usage = self.get_token_usage()

        total_input = token_usage.get("total_input_tokens", 0)
        total_output = token_usage.get("total_output_tokens", 0)
        total_cache_creation = token_usage.get("total_cache_creation_input_tokens", 0)
        total_cache_read = token_usage.get("total_cache_read_input_tokens", 0)

        cost = (
            (total_input / 1_000_000 * self.input_token_price)
            + (total_cache_creation / 1_000_000 * self.cache_creation_token_price)
            + (total_cache_read / 1_000_000 * self.cache_read_token_price)
            + (total_output / 1_000_000 * self.output_token_price)
        )

        summary_lines = []
        summary_lines.append("\n" + "-" * 20 + " Token Usage & Cost " + "-" * 20)
        summary_lines.append(f"Total Input Tokens (non-cache): {total_input}")
        summary_lines.append(
            f"Total Cache Creation Input Tokens: {total_cache_creation}"
        )
        summary_lines.append(f"Total Cache Read Input Tokens: {total_cache_read}")
        summary_lines.append(f"Total Output Tokens: {total_output}")
        summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))
        summary_lines.append(f"Input Token Price: ${self.input_token_price:.4f} USD")
        summary_lines.append(
            f"Cache Creation Token Price: ${self.cache_creation_token_price:.4f} USD"
        )
        summary_lines.append(
            f"Cache Read Token Price: ${self.cache_read_token_price:.4f} USD"
        )
        summary_lines.append(f"Output Token Price: ${self.output_token_price:.4f} USD")
        summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))
        summary_lines.append(f"Estimated Cost (with cache): ${cost:.4f} USD")
        summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))

        log_string = f"[Anthropic/{self.model_name}] Total Input: {total_input}, Cache Creation: {total_cache_creation}, Cache Read: {total_cache_read}, Output: {total_output}, Input Price: ${self.input_token_price:.4f} USD, Cache Creation Price: ${self.cache_creation_token_price:.4f} USD, Cache Read Price: ${self.cache_read_token_price:.4f} USD, Output Price: ${self.output_token_price:.4f} USD, Cost: ${cost:.4f} USD"

        return summary_lines, log_string

    def get_token_usage(self):
        """Get current cumulative Token usage - Anthropic implementation"""
        return self.token_usage.copy()

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
