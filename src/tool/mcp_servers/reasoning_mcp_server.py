# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import asyncio

from anthropic import Anthropic
from fastmcp import FastMCP
from openai import (
    OpenAI,
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    AuthenticationError,
)
from src.logging.logger import setup_mcp_logging


ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
ANTHROPIC_MODEL_NAME = os.environ.get(
    "ANTHROPIC_MODEL_NAME", "claude-3-7-sonnet-20250219"
)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL_NAME = os.environ.get("OPENAI_MODEL_NAME", "o3")

# Initialize FastMCP server
setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("reasoning-mcp-server")

_OPENAI_CLIENT: OpenAI | None = None
_ANTHROPIC_CLIENT: Anthropic | None = None


def _get_openai_client() -> OpenAI:
    """Return a shared OpenAI client for reasoning MCP."""
    global _OPENAI_CLIENT
    if _OPENAI_CLIENT is None:
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set for reasoning_mcp_server")
        _OPENAI_CLIENT = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
    return _OPENAI_CLIENT


def _get_anthropic_client() -> Anthropic:
    """Return a shared Anthropic client for reasoning MCP."""
    global _ANTHROPIC_CLIENT
    if _ANTHROPIC_CLIENT is None:
        if not ANTHROPIC_API_KEY:
            raise ValueError("ANTHROPIC_API_KEY is not set for reasoning_mcp_server")
        _ANTHROPIC_CLIENT = Anthropic(
            api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL
        )
    return _ANTHROPIC_CLIENT


@mcp.tool()
async def reasoning(question: str) -> str:
    """This tool is for pure text-based reasoning, analysis, and logical thinking. It integrates collected information, organizes final logic, and provides planning insights.

    IMPORTANT: This tool cannot access the internet, read files, program, or process multimodal content. It only performs pure text reasoning.

    Use this tool for:
    - Integrating and synthesizing collected information
    - Analyzing patterns and relationships in data
    - Logical reasoning and problem-solving
    - Planning and strategy development
    - Complex math problems, puzzles, riddles, and IQ tests

    DO NOT use this tool for simple and obvious questions.

    Args:
        question: The complex question or problem requiring step-by-step reasoning. Should include all relevant information needed to solve the problem.

    Returns:
        The reasoned answer to the question.
    """

    messages_for_llm = [
        {
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": question,
                }
            ],
        }
    ]

    if OPENAI_API_KEY:
        max_retries = 5
        client = _get_openai_client()
        for attempt in range(1, max_retries + 1):
            try:
                response = client.chat.completions.create(
                    model=OPENAI_MODEL_NAME,
                    messages=messages_for_llm,
                    extra_body={},
                )
                content = response.choices[0].message.content

                # Check if content is empty and retry if so
                if content and content.strip():
                    return content
                if attempt >= max_retries:
                    return f"Reasoning (OpenRouter Client) failed after {max_retries} retries: Empty response received\n"
                await asyncio.sleep(5 * (2**attempt))  # Exponential backoff
            except (APITimeoutError, RateLimitError) as e:
                if attempt >= max_retries:
                    return f"Reasoning (OpenRouter Client) failed after {max_retries} retries: {e}\n"
                await asyncio.sleep(5 * (2**attempt))
            except (AuthenticationError, APIConnectionError, APIError) as e:
                # Configuration or non-retryable server error: abort immediately
                return f"Reasoning (OpenRouter Client) failed due to configuration or authentication error: {e}\n"
            except Exception as e:
                # Unknown error: treat as non-retryable to avoid wasted attempts
                return f"Reasoning (OpenRouter Client) failed with unexpected error: {e}\n"
    else:
        max_retries = 5
        client = _get_anthropic_client()
        for attempt in range(1, max_retries + 1):
            try:
                response = client.messages.create(
                    model=ANTHROPIC_MODEL_NAME,
                    max_tokens=21000,
                    thinking={
                        "type": "enabled",
                        "budget_tokens": 19000,
                    },
                    messages=messages_for_llm,
                    stream=False,
                )
                content = response.content[-1].text

                # Check if content is empty and retry if so
                if content and content.strip():
                    return content
                if attempt >= max_retries:
                    return f"[ERROR]: Reasoning (Anthropic Client) failed after {max_retries} retries: Empty response received\n"
                await asyncio.sleep(5 * (2**attempt))
            except Exception as e:
                # Without fine-grained Anthropic error types, treat all as non-retryable beyond first failure
                if attempt >= max_retries:
                    return f"[ERROR]: Reasoning (Anthropic Client) failed after {max_retries} retries: {e}\n"
                await asyncio.sleep(5 * (2**attempt))


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
