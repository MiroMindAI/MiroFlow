# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import dataclasses
import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from omegaconf import DictConfig
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
class OpenCodeResponse:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    reasoning_tokens: int = 0
    finish_reason: str = "stop"


@dataclasses.dataclass
class OpenCodeChoice:
    message: Any
    finish_reason: str


@dataclasses.dataclass
class OpenCodeMessage:
    role: str
    content: str


@dataclasses.dataclass
class OpenCodeUsage:
    prompt_tokens: int
    completion_tokens: int
    prompt_tokens_details: Optional[Dict] = None
    completion_tokens_details: Optional[Dict] = None


@dataclasses.dataclass
class OpenCodeAPIResponse:
    choices: List[OpenCodeChoice]
    usage: OpenCodeUsage


@dataclasses.dataclass
class OpenCodeClient(LLMProviderClientBase):
    def _create_client(self, config: DictConfig):
        opencode_path = self.cfg.llm.get("opencode_path", "opencode")
        result = subprocess.run(
            [opencode_path, "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"OpenCode not found or not working: {result.stderr}")
        logger.info(f"OpenCode version: {result.stdout.strip()}")
        return opencode_path

    def _build_prompt_from_messages(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]]
    ) -> str:
        parts = []

        if system_prompt:
            parts.append(f"<system>\n{system_prompt}\n</system>\n")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "text":
                        text_parts.append(item.get("text", ""))
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = "\n".join(text_parts)

            if role == "system":
                parts.append(f"<system>\n{content}\n</system>\n")
            elif role == "user":
                parts.append(f"<user>\n{content}\n</user>\n")
            elif role == "assistant":
                parts.append(f"<assistant>\n{content}\n</assistant>\n")
            elif role == "tool":
                parts.append(f"<tool_result>\n{content}\n</tool_result>\n")

        return "\n".join(parts)

    async def _run_opencode(self, prompt: str) -> OpenCodeResponse:
        opencode_path = self.client
        model = self.model_name

        cmd = [
            opencode_path,
            "run",
            "--model", model,
            "--format", "json",
            prompt
        ]

        logger.debug(f"Running OpenCode: {' '.join(cmd[:5])}...")

        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0 and not stdout:
            error_msg = stderr.decode() if stderr else "Unknown error"
            logger.error(f"OpenCode failed: {error_msg}")
            raise RuntimeError(f"OpenCode failed: {error_msg}")

        response_text = ""
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0
        reasoning_tokens = 0
        finish_reason = "stop"

        for line in stdout.decode().strip().split("\n"):
            if not line:
                continue
            try:
                event = json.loads(line)
                event_type = event.get("type", "")

                if event_type == "text":
                    part = event.get("part", {})
                    response_text += part.get("text", "")

                elif event_type == "step_finish":
                    part = event.get("part", {})
                    finish_reason = part.get("reason", "stop")
                    tokens = part.get("tokens", {})
                    input_tokens += tokens.get("input", 0)
                    output_tokens += tokens.get("output", 0)
                    reasoning_tokens += tokens.get("reasoning", 0)
                    cache = tokens.get("cache", {})
                    cached_tokens += cache.get("read", 0)

                elif event_type == "error":
                    error_data = event.get("error", {})
                    error_msg = error_data.get("data", {}).get("message", str(error_data))
                    if "context" in error_msg.lower() or "token" in error_msg.lower():
                        raise ContextLimitError(error_msg)
                    raise RuntimeError(f"OpenCode API error: {error_msg}")

            except json.JSONDecodeError:
                logger.warning(f"Failed to parse JSON line: {line}")
                continue

        return OpenCodeResponse(
            text=response_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            reasoning_tokens=reasoning_tokens,
            finish_reason=finish_reason,
        )

    @retry(
        wait=wait_exponential(multiplier=5),
        stop=stop_after_attempt(3),
        retry=retry_if_not_exception_type(ContextLimitError),
    )
    async def _create_message(
        self,
        system_prompt: str,
        messages: List[Dict[str, Any]],
        tools_definitions,
        keep_tool_result: int = -1,
    ):
        logger.debug("Calling OpenCode LLM")

        messages_copy = self._remove_tool_result_from_messages(
            messages, keep_tool_result
        )

        prompt = self._build_prompt_from_messages(system_prompt, messages_copy)

        try:
            response = await self._run_opencode(prompt)

            if not response.text.strip():
                if response.finish_reason == "length":
                    raise ContextLimitError("Response truncated due to maximum length")
                logger.warning("OpenCode returned empty response")

            message = OpenCodeMessage(role="assistant", content=response.text)
            choice = OpenCodeChoice(message=message, finish_reason=response.finish_reason)
            usage = OpenCodeUsage(
                prompt_tokens=response.input_tokens,
                completion_tokens=response.output_tokens,
                prompt_tokens_details={"cached_tokens": response.cached_tokens},
                completion_tokens_details={"reasoning_tokens": response.reasoning_tokens},
            )

            return OpenCodeAPIResponse(choices=[choice], usage=usage)

        except asyncio.CancelledError:
            logger.warning("OpenCode API call was cancelled")
            raise
        except ContextLimitError:
            raise
        except Exception as e:
            error_str = str(e).lower()
            if "context" in error_str or "token" in error_str or "length" in error_str:
                raise ContextLimitError(f"Context limit exceeded: {e}")
            logger.error(f"OpenCode LLM call failed: {e}")
            raise

    def _clean_user_content_from_response(self, text: str) -> str:
        pattern = r"\n\nUser:.*?(?=<use_mcp_tool>|$)"
        return re.sub(pattern, "", text, flags=re.MULTILINE | re.DOTALL)

    def process_llm_response(
        self, llm_response, message_history, agent_type="main"
    ) -> tuple[str, bool]:
        if not llm_response or not llm_response.choices:
            logger.error("LLM did not return a valid response.")
            return "", True

        choice = llm_response.choices[0]
        assistant_response_text = choice.message.content or ""

        assistant_response_text = self._clean_user_content_from_response(
            assistant_response_text
        )

        message_history.append(
            {"role": "assistant", "content": assistant_response_text}
        )

        logger.debug(f"LLM Response: {assistant_response_text[:500]}...")
        return assistant_response_text, False

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        from src.utils.parsing_utils import parse_llm_response_for_tool_calls
        return parse_llm_response_for_tool_calls(assistant_response_text)

    def update_message_history(
        self, message_history, tool_call_info, tool_calls_exceeded=False
    ):
        tool_call_info = [item for item in tool_call_info if item[1]["type"] == "text"]

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

        output_parts = []

        if total_calls > 1:
            if tool_calls_exceeded:
                output_parts.append(
                    f"You made too many tool calls. I can only afford to process {len(valid_tool_calls)} valid tool calls in this turn."
                )
            else:
                output_parts.append(
                    f"I have processed {len(valid_tool_calls)} valid tool calls in this turn."
                )

            for i, (tool_id, content) in enumerate(valid_tool_calls, 1):
                output_parts.append(f"Valid tool call {i} result:\n{content['text']}")

            for i, (tool_id, content) in enumerate(bad_tool_calls, 1):
                output_parts.append(f"Failed tool call {i} result:\n{content['text']}")
        else:
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

    def handle_max_turns_reached_summary_prompt(self, message_history, summary_prompt):
        if message_history[-1]["role"] == "user":
            last_user_message = message_history.pop()
            return (
                last_user_message["content"][0]["text"]
                + "\n\n-----------------\n\n"
                + summary_prompt
            )
        else:
            return summary_prompt

    def _extract_usage_from_response(self, response):
        if not hasattr(response, "usage") or response.usage is None:
            return {
                "input_tokens": 0,
                "cached_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
            }

        usage = response.usage
        prompt_details = usage.prompt_tokens_details or {}
        completion_details = usage.completion_tokens_details or {}

        return {
            "input_tokens": usage.prompt_tokens,
            "cached_tokens": prompt_details.get("cached_tokens", 0),
            "output_tokens": usage.completion_tokens,
            "reasoning_tokens": completion_details.get("reasoning_tokens", 0),
        }
