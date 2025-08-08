import os

from anthropic import Anthropic
from fastmcp import FastMCP
from openai import OpenAI
import asyncio

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.environ.get("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.environ.get(
    "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
)

# Initialize FastMCP server
mcp = FastMCP("reasoning-mcp-server")


@mcp.tool()
async def reasoning(question: str) -> str:
    """You can use this tool use solve hard math problem, puzzle, riddle and IQ test question that requries a lot of chain of thought efforts.
    DO NOT use this tool for simple and obvious question.

    Args:
        question: The complex question or problem requiring step-by-step reasoning. Should include all relevant information needed to solve the problem..

    Returns:
        The answer to the question.
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

    if OPENROUTER_API_KEY:
        max_retries = 5
        for attempt in range(1, max_retries + 1):
            try:
                client = OpenAI(
                    api_key=OPENROUTER_API_KEY, base_url=OPENROUTER_BASE_URL
                )
                response = client.chat.completions.create(
                    model="anthropic/claude-3-7-sonnet:thinking",
                    messages=messages_for_llm,
                    extra_body={},
                )
                content = response.choices[0].message.content

                # Check if content is empty and retry if so
                if content and content.strip():
                    return content
                else:
                    if attempt >= max_retries:
                        return f"Reasoning (OpenRouter Client) failed after {max_retries} retries: Empty response received\n"
                    await asyncio.sleep(
                        5 * (2**attempt)
                    )  # Exponential backoff with max 30s
                    continue

            except Exception as e:
                if attempt >= max_retries:
                    return f"Reasoning (OpenRouter Client) failed after {max_retries} retries: {e}\n"
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
                    model="claude-3-7-sonnet-20250219",
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
                else:
                    if attempt >= max_retries:
                        return f"[ERROR]: Reasoning (Anthropic Client) failed after {max_retries} retries: Empty response received\n"
                    await asyncio.sleep(
                        5 * (2**attempt)
                    )  # Exponential backoff with max 30s
                    continue

            except Exception as e:
                if attempt >= max_retries:
                    return f"[ERROR]: Reasoning (Anthropic Client) failed after {max_retries} retries: {e}\n"
                await asyncio.sleep(
                    5 * (2**attempt)
                )  # Exponential backoff with max 30s


if __name__ == "__main__":
    mcp.run(transport="stdio")
