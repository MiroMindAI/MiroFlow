# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os

from anthropic import Anthropic
from fastmcp import FastMCP
from openai import OpenAI
import asyncio
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


@mcp.tool()
async def reasoning(question: str) -> dict:
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
        for attempt in range(1, max_retries + 1):
            try:
                client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
                response = client.chat.completions.create(
                    model=OPENAI_MODEL_NAME,
                    messages=messages_for_llm,
                    extra_body={},
                )
                content = response.choices[0].message.content

                # Check if content is empty and retry if so
                if content and content.strip():
                    if not hasattr(response, "usage"):
                        return {"text": content, "usage": {}}
                    else:
                        usage = response.usage
                        cache_tokens = getattr(
                            getattr(usage, "prompt_tokens_details", {}),
                            "cached_tokens",
                            0,
                        )
                        text_input_tokens = getattr(usage, "prompt_tokens", 0)
                        text_output_tokens = getattr(usage, "completion_tokens", 0)
                    return {
                        "text": content,
                        "usage": {
                            f"reasoning_openrouter_{OPENAI_MODEL_NAME}": {
                                "cache_read": cache_tokens,
                                "input_text": text_input_tokens,
                                "output_text": text_output_tokens,
                                "cost": getattr(usage, "cost", 0),
                            }
                        },
                    }
                else:
                    if attempt >= max_retries:
                        return {
                            "text": f"Reasoning (OpenRouter Client) failed after {max_retries} retries: Empty response received\n",
                            "usage": {},
                        }
                    await asyncio.sleep(
                        5 * (2**attempt)
                    )  # Exponential backoff with max 30s
                    continue

            except Exception as e:
                if attempt >= max_retries:
                    return {
                        "text": f"Reasoning (OpenRouter Client) failed after {max_retries} retries: {e}\n",
                        "usage": {},
                    }
                await asyncio.sleep(
                    5 * (2**attempt)
                )  # Exponential backoff with max 30s
    else:
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                client = Anthropic(
                    api_key=ANTHROPIC_API_KEY, base_url=ANTHROPIC_BASE_URL
                )
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
                    if not hasattr(response, "usage"):
                        usage = {}
                    else:
                        usage_temp = response.usage
                        usage = {
                            f"reasoning_anthropic_{ANTHROPIC_MODEL_NAME}": {
                                "input": getattr(usage_temp, "input_tokens", 0),
                                "output": getattr(usage_temp, "output_tokens", 0),
                                "cache_read": getattr(
                                    usage_temp, "cache_read_input_tokens", 0
                                ),
                                "cache_write": getattr(
                                    usage_temp, "cache_creation_input_tokens", 0
                                ),
                            }
                        }
                    return {"text": content, "usage": usage}
                else:
                    if attempt >= max_retries:
                        return {
                            "text": f"[ERROR]: Reasoning (Anthropic Client) failed after {max_retries} retries: Empty response received\n",
                            "usage": {},
                        }
                    await asyncio.sleep(
                        5 * (2**attempt)
                    )  # Exponential backoff with max 30s
                    continue

            except Exception as e:
                if attempt >= max_retries:
                    return {
                        "text": f"[ERROR]: Reasoning (Anthropic Client) failed after {max_retries} retries: {e}\n",
                        "usage": {},
                    }
                await asyncio.sleep(
                    5 * (2**attempt)
                )  # Exponential backoff with max 30s


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
