#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Simple test script for Kimi K2.5 model via OpenRouter"""

import asyncio
import os
from pathlib import Path
from openai import AsyncOpenAI

# Load .env file if it exists
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    print(f"Loading environment from {env_file}")
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                if value and value != "xxxx":
                    os.environ[key] = value


async def test_kimi():
    # Get API credentials from environment
    api_key = os.getenv("OPENROUTER_API_KEY")
    base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

    if not api_key:
        print("Error: OPENROUTER_API_KEY environment variable not set")
        return

    print("Testing Kimi K2.5 model via OpenRouter")
    print(f"Base URL: {base_url}")
    print(f"API Key: {api_key[:10]}..." if api_key else "API Key: Not set")
    print("-" * 50)

    # Create client
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=60,
    )

    # Test prompt
    messages = [
        {
            "role": "user",
            "content": "你好！请用中文简单介绍一下你自己，并解决这个简单的数学问题：25 * 4 + 17 = ?",
        }
    ]

    # Try different model names
    model_names = [
        "moonshot/kimi-k2.5",
        "moonshot-v1-128k",
        "moonshot-v1-32k",
        "moonshot-v1-8k",
    ]

    for model_name in model_names:
        try:
            print(f"\nTrying model: {model_name}...")
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=1.0,
                max_tokens=1000,
            )

            print("\n✓ Response received successfully!")
            print("-" * 50)
            print("Model:", response.model)
            print("Finish reason:", response.choices[0].finish_reason)
            print("\nResponse content:")
            print(response.choices[0].message.content)
            print("-" * 50)

            if hasattr(response, "usage"):
                print("\nUsage:")
                print(f"  Prompt tokens: {response.usage.prompt_tokens}")
                print(f"  Completion tokens: {response.usage.completion_tokens}")
                print(f"  Total tokens: {response.usage.total_tokens}")

            # Success, exit loop
            break

        except Exception as e:
            print(f"✗ Failed: {e}")
            if model_name == model_names[-1]:  # Last attempt
                print("\nAll model attempts failed.")
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_kimi())
