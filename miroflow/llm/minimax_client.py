# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
MiniMax LLM client - OpenAI-compatible provider for MiniMax M2.7 models.

Supported models:
  - MiniMax-M2.7: Peak performance, ultimate value (default)
  - MiniMax-M2.7-highspeed: Same performance, faster and more agile

API docs: https://platform.minimax.io/docs/api-reference/text-openai-api
"""

from typing import Any, Dict, List

from omegaconf import DictConfig
from openai import AsyncOpenAI, OpenAI
from tenacity import retry, stop_after_attempt, wait_fixed

from miroflow.llm.base import LLMClientBase
from miroflow.logging.task_tracer import get_tracer

logger = get_tracer()

# MiniMax models supported
MINIMAX_MODELS = {"MiniMax-M2.7", "MiniMax-M2.7-highspeed"}

# MiniMax temperature range: (0.0, 1.0]
MINIMAX_TEMP_MIN = 0.01
MINIMAX_TEMP_MAX = 1.0


def _clamp_temperature(temperature: float) -> float:
    """Clamp temperature to MiniMax's valid range (0.0, 1.0]."""
    if temperature <= 0.0:
        return MINIMAX_TEMP_MIN
    if temperature > MINIMAX_TEMP_MAX:
        return MINIMAX_TEMP_MAX
    return temperature


class MiniMaxClient(LLMClientBase):
    """
    MiniMax LLM client using OpenAI-compatible API.

    MiniMax provides high-performance language models accessible via
    an OpenAI-compatible endpoint at https://api.minimax.io/v1.

    Configuration example (YAML):
        provider_class: "MiniMaxClient"
        model_name: "MiniMax-M2.7"
        api_key: ${oc.env:MINIMAX_API_KEY,???}
        base_url: ${oc.env:MINIMAX_BASE_URL,https://api.minimax.io/v1}
    """

    def _create_client(self, config: DictConfig):
        """Create configured OpenAI-compatible client for MiniMax."""
        if self.async_client:
            return AsyncOpenAI(
                api_key=self.cfg.api_key,
                base_url=self.cfg.base_url,
                timeout=1800,
            )
        else:
            return OpenAI(
                api_key=self.cfg.api_key,
                base_url=self.cfg.base_url,
                timeout=1800,
            )

    @retry(wait=wait_fixed(10), stop=stop_after_attempt(10))
    async def _create_message(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_definitions,
        keep_tool_result: int = -1,
    ):
        """Send message to MiniMax API via OpenAI-compatible endpoint."""
        logger.debug(f" Calling MiniMax LLM ({'async' if self.async_client else 'sync'})")

        # Inject system prompt
        if system_prompt:
            if messages and messages[0]["role"] in ["system", "developer"]:
                messages[0] = {
                    "role": "system",
                    "content": [dict(type="text", text=system_prompt)],
                }
            else:
                messages.insert(
                    0,
                    {
                        "role": "system",
                        "content": [dict(type="text", text=system_prompt)],
                    },
                )

        messages_copy = self._remove_tool_result_from_messages(
            messages, keep_tool_result
        )

        if tools_definitions:
            tool_list = await self.convert_tool_definition_to_tool_call(
                tools_definitions
            )
        else:
            tool_list = None

        # Clamp temperature to MiniMax valid range
        temperature = _clamp_temperature(self.temperature)

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

        try:
            if self.async_client:
                response = await self.client.chat.completions.create(**params)
            else:
                response = self.client.chat.completions.create(**params)

            logger.debug(
                f"MiniMax LLM call status: {getattr(response.choices[0], 'finish_reason', 'N/A')}"
            )
            return response
        except Exception as e:
            logger.exception(f"MiniMax LLM call failed: {str(e)}")
            raise

    def process_llm_response(self, llm_response) -> tuple[str, bool, dict]:
        """Process MiniMax LLM response (OpenAI-compatible format)."""
        if not llm_response or not llm_response.choices:
            logger.debug("Error: MiniMax LLM did not return a valid response.")
            return "", True, {}

        finish_reason = llm_response.choices[0].finish_reason

        if finish_reason == "stop":
            text = llm_response.choices[0].message.content or ""
            return text, False, {"role": "assistant", "content": text}

        if finish_reason == "tool_calls":
            tool_calls = llm_response.choices[0].message.tool_calls
            text = llm_response.choices[0].message.content or ""

            if not text:
                descriptions = []
                for tc in tool_calls:
                    descriptions.append(
                        f"Using tool {tc.function.name} with arguments: {tc.function.arguments}"
                    )
                text = "\n".join(descriptions)

            assistant_message = {
                "role": "assistant",
                "content": text,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in tool_calls
                ],
            }
            return text, False, assistant_message

        if finish_reason == "length":
            text = llm_response.choices[0].message.content or ""
            if text == "":
                text = "LLM response is empty. This is likely due to thinking block used up all tokens."
            return text, False, {"role": "assistant", "content": text}

        raise ValueError(f"Unsupported finish reason: {finish_reason}")

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """Extract tool call information from MiniMax response."""
        from miroflow.utils.parsing_utils import parse_llm_response_for_tool_calls

        if llm_response.choices[0].finish_reason == "tool_calls":
            return parse_llm_response_for_tool_calls(
                llm_response.choices[0].message.tool_calls
            )
        return [], []

    def update_message_history(
        self, message_history, tool_call_info, tool_calls_exceeded: bool = False
    ):
        """Update message history with tool call results."""
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
        """Handle max turns reached summary prompt."""
        return summary_prompt
