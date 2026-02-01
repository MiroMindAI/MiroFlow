#!/usr/bin/env python3
"""Test script to verify Kimi model integration with OpenRouter client"""

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


async def test_kimi_model():
    """Test Kimi model with a simple message"""

    # Load config
    config = OmegaConf.load("config/llm/base_kimi_k25.yaml")

    # Resolve environment variables
    config = OmegaConf.to_container(config, resolve=True)
    config = OmegaConf.create(config)

    print(f"Testing with model: {config.model_name}")
    print(f"Base URL: {config.openrouter_base_url}")

    # Create client
    client = OpenRouterClient(config)

    # Test message
    system_prompt = "You are a helpful assistant."
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello! Please respond with a short greeting."}
            ],
        }
    ]

    print("\nSending test message...")
    try:
        response = await client._create_message(
            system_prompt=system_prompt,
            messages=messages,
            tools_definitions={},
            keep_tool_result=-1,
        )

        print("\n✓ Success! Response received:")
        print(f"  Finish reason: {response.choices[0].finish_reason}")
        print(f"  Content: {response.choices[0].message.content[:100]}...")

        # Check if reasoning fields are present (Kimi specific)
        if hasattr(response.choices[0].message, "reasoning"):
            print("\n  ✓ Reasoning field present (Kimi model)")

        return True

    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_kimi_model())
    exit(0 if success else 1)
