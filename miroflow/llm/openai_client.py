# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import re
from typing import Any, Dict, List, Tuple

import tiktoken
from omegaconf import DictConfig
from openai import AsyncOpenAI, OpenAI
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from miroflow.llm.base import LLMClientBase, ContextLimitError
from miroflow.logging.task_tracer import get_tracer

logger = get_tracer()

# OpenAI reasoning models only support temperature=1
OPENAI_REASONING_MODEL_SET = set(
    ["o1", "o3", "o3-mini", "o4-mini", "gpt-5", "gpt-5-2025-08-07"]
)


class UnifiedOpenAIClient(LLMClientBase):
    """
    Unified client merging:
      - code1: OpenAI native tool_calls protocol (+ optional oai_tool_thinking)
      - code2: text-based tool protocol + cache_control + context-limit handling + output cleaning

    Key knobs (expected on cfg; provide defaults in base if absent):
      - async_client: bool
      - disable_cache_control: bool
      - tool_mode: str in {"auto","openai_native","text_protocol"}  (optional; default "auto")
      - clean_user_echo: bool (optional; default True)
      - oai_tool_thinking: bool (optional; default False)
    """

    # -----------------------------
    # Client construction
    # -----------------------------
    def __init__(self, cfg: DictConfig):
        super().__init__(cfg)
        # code1 flag
        self.oai_tool_thinking = getattr(self.cfg, "oai_tool_thinking", False)
        # code2 flags
        self.disable_cache_control = getattr(self.cfg, "disable_cache_control", True)
        self.clean_user_echo = getattr(self.cfg, "clean_user_echo", True)
        self.tool_mode = (
            (getattr(self.cfg, "tool_mode", "auto") or "auto").strip().lower()
        )

    def _create_client(self, config: DictConfig):
        """Create configured OpenAI client"""
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

    # -----------------------------
    # High-level request flow
    # -----------------------------
    @retry(
        wait=wait_exponential(multiplier=5),
        stop=stop_after_attempt(10),
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
        Send message to OpenAI API (async/sync supported).
        Compatible with:
          - OpenAI native tools: tools_definitions -> tools param -> tool_calls responses
          - Text tool protocol: parse tool calls from assistant text and inject tool results back

        Returns: OpenAI API response object
        """
        logger.debug(f" Calling LLM ({'async' if self.async_client else 'sync'})")

        # 1) Decide tool mode for this call
        tool_mode = self._decide_tool_mode(tools_definitions)

        # 2) Build processed messages (system injection + tool trimming + cache control)
        processed_messages = self._build_messages(
            system_prompt=system_prompt,
            messages=messages,
            keep_tool_result=keep_tool_result,
        )

        # 3) Build tool payload if needed
        tool_list = None
        if tool_mode == "openai_native" and tools_definitions:
            tool_list = await self.convert_tool_definition_to_tool_call(
                tools_definitions
            )

        # 4) Build request params (leave min_p/top_k policy for later)
        params = self._build_params(processed_messages, tool_list=tool_list)

        # 5) Execute call (may do oai_tool_thinking two-step only for native tools)
        try:
            if self.oai_tool_thinking and tool_mode == "openai_native":
                response = await self._handle_oai_tool_thinking(
                    params, messages, self.async_client
                )
            else:
                response = await self._create_completion(params, self.async_client)

            # 6) Validate and raise non-retriable context limit errors
            self._validate_response_or_raise(response, params)

            # Track token usage for proactive context limit management
            if hasattr(response, "usage") and response.usage:
                self.last_call_tokens = {
                    "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) or 0,
                    "completion_tokens": getattr(response.usage, "completion_tokens", 0)
                    or 0,
                }

            logger.debug(
                f"LLM call finish_reason: {getattr(response.choices[0], 'finish_reason', 'N/A')}"
            )
            return response

        except asyncio.CancelledError:
            logger.exception("[WARNING] LLM API call was cancelled during execution")
            raise
        except Exception as e:
            # Map common context-limit strings to ContextLimitError (non-retriable)
            self._maybe_raise_context_limit(e)
            logger.error(
                f"LLM call failed [{type(e).__name__}]: {str(e)}",
                exc_info=True,
            )
            raise

    # -----------------------------
    # Tool mode decision
    # -----------------------------
    def _decide_tool_mode(self, tools_definitions) -> str:
        """
        Decide which tool protocol to use for this call.
        - If cfg.tool_mode is explicit, honor it.
        - If auto:
            - if tools_definitions is provided -> prefer native
            - else -> text_protocol (no structured tools to send)
        """
        if self.tool_mode in ("native", "text_protocol"):
            return self.tool_mode

        # auto
        if tools_definitions:
            return "native"
        return "text_protocol"

    # -----------------------------
    # Message building / preprocessing
    # -----------------------------
    def _is_oai_new_model(self) -> bool:
        mn = (self.model_name or "").lower()
        return (
            mn.startswith("o1")
            or mn.startswith("o3")
            or mn.startswith("o4")
            or mn.startswith("gpt-4.1")
            or mn.startswith("gpt-4o")
            or mn.startswith("gpt-5")
        )

    def _inject_system_prompt(
        self, system_prompt: str, messages: List[Dict[str, Any]]
    ) -> None:
        """Put the system prompt into messages[0] with correct role."""
        if not system_prompt:
            return
        target_role = "developer" if self._is_oai_new_model() else "system"

        if messages and messages[0].get("role") in ["system", "developer"]:
            messages[0] = {
                "role": target_role,
                "content": [dict(type="text", text=system_prompt)],
            }
        else:
            messages.insert(
                0,
                {
                    "role": target_role,
                    "content": [dict(type="text", text=system_prompt)],
                },
            )

    def _build_messages(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        keep_tool_result: int,
    ) -> List[Dict[str, Any]]:
        """
        1) Inject system prompt (mutates messages)
        2) Remove tool results beyond keep_tool_result
        3) Apply cache control (optional)
        """
        self._inject_system_prompt(system_prompt, messages)

        messages_copy = self._remove_tool_result_from_messages(
            messages, keep_tool_result
        )

        if self.disable_cache_control:
            return messages_copy
        return self._apply_cache_control(messages_copy)

    # -----------------------------
    # Params building
    # -----------------------------
    def _build_params(
        self,
        processed_messages: List[Dict[str, Any]],
        tool_list=None,
    ) -> Dict[str, Any]:
        """
        Build completion parameters.
        NOTE: min_p/top_k policy intentionally left 'as-is' for later decision.
        """
        # reasoning model temperature rule
        if self.model_name in OPENAI_REASONING_MODEL_SET:
            temperature = 1.0
        else:
            temperature = self.temperature

        params: Dict[str, Any] = {
            "model": self.model_name,
            "temperature": temperature,
            "max_completion_tokens": self.max_tokens,
            "messages": processed_messages,
            "stream": False,
        }

        # reasoning_effort is used in both codepaths in your current codebase;
        # keep it for compatibility when present.
        if getattr(self, "reasoning_effort", None) is not None:
            params["reasoning_effort"] = self.reasoning_effort

        if tool_list is not None:
            params["tools"] = tool_list

        if self.top_p != 1.0:
            params["top_p"] = self.top_p

        # Leave these as placeholders: decide later whether to use params vs extra_body
        # if self.min_p != 0.0: params["min_p"] = self.min_p
        # if self.top_k != -1: params["top_k"] = self.top_k
        # if getattr(self, "repetition_penalty", 1.0) != 1.0: params["repetition_penalty"] = self.repetition_penalty

        return params

    # -----------------------------
    # Completion helpers
    # -----------------------------
    async def _create_completion(self, params: Dict[str, Any], is_async: bool):
        if is_async:
            return await self.client.chat.completions.create(**params)
        else:
            return self.client.chat.completions.create(**params)

    async def _handle_oai_tool_thinking(
        self,
        params: Dict[str, Any],
        messages: List[Dict[str, Any]],
        is_async: bool,
    ):
        """
        Two-step:
          1) tool_choice="none" to get text
          2) allow tool calls; if tool_calls returned, keep step1 text as message.content
        Only meaningful for OpenAI native tool protocol.
        """
        # Step 1
        params["tool_choice"] = "none"
        response = await self._create_completion(params, is_async)

        text_reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": text_reply})

        # Step 2
        params["messages"] = messages
        del params["tool_choice"]
        response_tool = await self._create_completion(params, is_async)

        if response_tool.choices[0].finish_reason == "tool_calls":
            response_tool.choices[0].message.content = text_reply
            response = response_tool

        # Pop temp assistant
        messages.pop()
        return response

    # -----------------------------
    # Error handling & validation
    # -----------------------------
    def _validate_response_or_raise(self, response, params: Dict[str, Any]) -> None:
        if (
            response is None
            or not getattr(response, "choices", None)
            or len(response.choices) == 0
        ):
            raise Exception(f"LLM call failed [rare case]: response = {response}")

        fr = response.choices[0].finish_reason
        if fr == "length":
            logger.debug("finish_reason is 'length', triggering ContextLimitError")
            raise ContextLimitError(
                "(finish_reason=length) Response truncated due to maximum context length"
            )

        # Some rare cases: stop but empty
        if fr == "stop":
            content = (response.choices[0].message.content or "").strip()
            if content == "":
                raise Exception("LLM finish_reason is 'stop', but content is empty")

    def _maybe_raise_context_limit(self, e: Exception) -> None:
        error_str = str(e)
        if (
            "Input is too long for requested model" in error_str
            or "input length and `max_tokens` exceed context limit" in error_str
            or "maximum context length" in error_str
            or "prompt is too long" in error_str
            or "exceeds the maximum length" in error_str
            or "exceeds the maximum allowed length" in error_str
            or "Input tokens exceed the configured limit" in error_str
        ):
            logger.debug(f"Context limit exceeded: {error_str}")
            raise ContextLimitError(f"Context limit exceeded: {error_str}")

    # -----------------------------
    # Response parsing / post-processing
    # -----------------------------
    def _clean_user_content_from_response(self, text: str) -> str:
        """
        Remove content between \\n\\nUser: and <use_mcp_tool> in assistant response
        (if no <use_mcp_tool>, remove to end).
        """
        pattern = r"\n\nUser:.*?(?=<use_mcp_tool>|$)"
        return re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)

    def process_llm_response(self, llm_response) -> Tuple[str, bool, dict]:
        """
        Unified response processing.

        Returns:
            (response_text, is_invalid, assistant_message)
        """
        if not llm_response or not getattr(llm_response, "choices", None):
            logger.error("LLM did not return a valid response.")
            return "", True, {}

        fr = llm_response.choices[0].finish_reason

        if fr == "stop":
            text = llm_response.choices[0].message.content or ""
            if self.clean_user_echo:
                text = self._clean_user_content_from_response(text)
            assistant_message = {"role": "assistant", "content": text}
            return text, False, assistant_message

        if fr == "tool_calls":
            # OpenAI native tool_calls
            text = llm_response.choices[0].message.content or ""
            if self.clean_user_echo and text:
                text = self._clean_user_content_from_response(text)

            tool_calls = llm_response.choices[0].message.tool_calls
            # If there's no text, generate a description
            if not text:
                desc = []
                for tc in tool_calls:
                    desc.append(
                        f"Using tool {tc.function.name} with arguments: {tc.function.arguments}"
                    )
                text = "\n".join(desc)

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

        if fr == "length":
            text = llm_response.choices[0].message.content or ""
            if text == "":
                text = "LLM response is empty. This is likely due to thinking block used up all tokens."
            elif self.clean_user_echo:
                text = self._clean_user_content_from_response(text)
            assistant_message = {"role": "assistant", "content": text}
            return text, False, assistant_message

        # Fallback
        logger.error(f"Unsupported finish reason: {fr}")
        text = f"Successful response, but unsupported finish reason: {fr}"
        return text, False, {"role": "assistant", "content": text}

    # -----------------------------
    # Tool call extraction (dual protocol)
    # -----------------------------
    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        """
        Extract tool call information in a protocol-compatible way.
        - If response has native tool_calls -> parse those
        - Else -> parse from text
        """
        from miroflow.utils.parsing_utils import parse_llm_response_for_tool_calls

        try:
            if (
                llm_response
                and llm_response.choices
                and llm_response.choices[0].finish_reason == "tool_calls"
                and getattr(llm_response.choices[0].message, "tool_calls", None)
            ):
                return parse_llm_response_for_tool_calls(
                    llm_response.choices[0].message.tool_calls
                )
        except Exception:
            # fall back to text parsing
            logger.debug(
                "Native tool_calls parsing failed, falling back to text parsing"
            )

        return parse_llm_response_for_tool_calls(assistant_response_text)

    def update_message_history(
        self,
        message_history,
        tool_call_info,
        tool_calls_exceeded: bool = False,
    ):
        """
        Update message history with tool results.
        Supports both:
          - Native OpenAI tool role messages (tool_call_id)
          - Text protocol: merge tool results into a single user message
        """
        # Decide protocol based on tool_call_info shape / cfg hint
        # If your parsing utils returns OpenAI-like ids + content dicts, we can route by cfg.tool_mode.
        mode = self.tool_mode
        if mode == "auto":
            # heuristic: if message_history expects role=tool usage, prefer native unless explicitly text_protocol
            mode = "native"

        if mode == "native":
            # code1 behavior: append role=tool messages
            for cur_call_id, tool_result in tool_call_info:
                message_history.append(
                    {
                        "role": "tool",
                        "tool_call_id": cur_call_id,
                        "content": tool_result["text"],
                    }
                )
            return message_history

        # text_protocol behavior (code2): filter, summarize, then append as a "user" message
        tool_call_info = [
            item for item in tool_call_info if item[1].get("type") == "text"
        ]

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
        output_parts: List[str] = []

        if total_calls > 1:
            if tool_calls_exceeded:
                output_parts.append(
                    f"You made too many tool calls. I can only afford to process {len(valid_tool_calls)} valid tool calls in this turn."
                )
            else:
                output_parts.append(
                    f"I have processed {len(valid_tool_calls)} valid tool calls in this turn."
                )

            for i, (_, content) in enumerate(valid_tool_calls, 1):
                output_parts.append(f"Valid tool call {i} result:\n{content['text']}")
            for i, (_, content) in enumerate(bad_tool_calls, 1):
                output_parts.append(f"Failed tool call {i} result:\n{content['text']}")
        else:
            for _, content in valid_tool_calls:
                output_parts.append(content["text"])
            for _, content in bad_tool_calls:
                output_parts.append(content["text"])

        merged_text = "\n\n".join(output_parts)
        message_history.append(
            {
                "role": "user",
                "content": [{"type": "text", "text": merged_text}],
            }
        )
        return message_history

    # -----------------------------
    # Misc helpers carried over
    # -----------------------------
    def parse_llm_response(self, llm_response) -> str:
        if not llm_response or not getattr(llm_response, "choices", None):
            raise ValueError("LLM did not return a valid response.")
        return llm_response.choices[0].message.content

    def _estimate_tokens(self, text: str) -> int:
        """Use tiktoken to estimate token count of text"""
        if not hasattr(self, "encoding"):
            try:
                self.encoding = tiktoken.get_encoding("o200k_base")
            except Exception:
                self.encoding = tiktoken.get_encoding("cl100k_base")

        try:
            return len(self.encoding.encode(text))
        except Exception:
            return len(text) // 4

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        """Preserve code2 behavior: if last is user, pop and prepend to summary prompt."""
        if message_history and message_history[-1].get("role") == "user":
            last_user_message = message_history.pop()
            return (
                last_user_message["content"][0]["text"]
                + "\n\n-----------------\n\n"
                + summary_prompt
            )
        return summary_prompt

    def _apply_cache_control(self, messages):
        """Apply cache control to the last user message and system/developer message (if applicable)."""
        cached_messages = []
        user_turns_processed = 0
        for turn in reversed(messages):
            if (turn["role"] == "user" and user_turns_processed < 1) or (
                turn["role"] in ("system", "developer")
            ):
                new_content = []
                processed_text = False
                if isinstance(turn.get("content"), list):
                    for item in turn["content"]:
                        if (
                            item.get("type") == "text"
                            and len(item.get("text", "")) > 0
                            and not processed_text
                        ):
                            text_item = item.copy()
                            text_item["cache_control"] = {"type": "ephemeral"}
                            new_content.append(text_item)
                            processed_text = True
                        else:
                            new_content.append(item.copy())
                    cached_messages.append(
                        {"role": turn["role"], "content": new_content}
                    )
                else:
                    logger.debug(
                        "Warning: message content is not in expected list format, cache control not applied."
                    )
                    cached_messages.append(turn)
                user_turns_processed += 1
            else:
                cached_messages.append(turn)
        return list(reversed(cached_messages))
