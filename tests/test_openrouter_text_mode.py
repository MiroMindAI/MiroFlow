#!/usr/bin/env python3
"""Test Kimi model in text-only mode (no tool_calls)"""

import asyncio
import os
from pathlib import Path

# Set up environment
project_root = Path(__file__).parent
os.chdir(project_root)

# Load environment variables
from dotenv import load_dotenv  # noqa: E402

load_dotenv()

# Import the OpenRouter client
from src.llm.openrouter import OpenRouterClient  # noqa: E402
from omegaconf import OmegaConf  # noqa: E402


async def test_text_mode():
    """Test that model returns text format, not tool_calls"""

    # Load config
    config = OmegaConf.load("config/llm/base_kimi_k25.yaml")
    config = OmegaConf.to_container(config, resolve=True)
    config = OmegaConf.create(config)

    print(f"Model: {config.model_name}")
    print(f"use_tool_calls: {config.use_tool_calls}")

    # Create client
    client = OpenRouterClient(config)

    # Create a simple system prompt with tool instructions
    system_prompt = """You have access to these tools:
- search(query): Search the web
- calculate(expression): Calculate a math expression

Use XML format: <use_tool><tool_name>search</tool_name><arguments>{"query": "test"}</arguments></use_tool>"""

    messages = [
        {
            "role": "user",
            "content": [{"type": "text", "text": "Search for 'Python tutorial'"}],
        }
    ]

    # Provide empty tools_definitions since we want text mode
    tools_definitions = {}

    print("\nSending test message...")
    try:
        response = await client._create_message(
            system_prompt=system_prompt,
            messages=messages,
            tools_definitions=tools_definitions,
            keep_tool_result=-1,
        )

        print("\n✓ Success!")
        print(f"  Finish reason: {response.choices[0].finish_reason}")

        # Check if it's text mode or tool_calls mode
        if response.choices[0].finish_reason == "tool_calls":
            print("  ✗ ERROR: Model returned tool_calls format (should be text)")
            print(f"  Tool calls: {response.choices[0].message.tool_calls}")
            return False
        else:
            print("  ✓ Correct: Model returned text format")
            print(f"  Content preview: {response.choices[0].message.content[:200]}...")
            return True

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_text_mode())
    exit(0 if success else 1)
