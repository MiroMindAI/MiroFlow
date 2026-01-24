#!/usr/bin/env python3
"""
Simple test script to verify MiroThinker API connectivity.
"""

import asyncio
import os
import dotenv
from omegaconf import OmegaConf
from src.llm.factory import build_llm_client

# Load environment variables
dotenv.load_dotenv()


async def test_mirothinker_api():
    """Test MiroThinker API with a simple message"""

    # Create minimal config for MiroThinker
    llm_config = OmegaConf.create(
        {
            "provider_class": "MiroThinkerSGLangClient",
            "model_name": "dummy",  # or use actual model name if available
            "api_key": os.getenv("OAI_MIROTHINKER_API_KEY", "dummy_key"),
            "base_url": os.getenv(
                "OAI_MIROTHINKER_BASE_URL", "http://localhost:61005/v1"
            ),
            "temperature": 1.0,
            "top_p": 0.95,
            "min_p": 0.0,
            "top_k": -1,
            "max_tokens": 16384,
            "max_context_length": -1,
            "async_client": True,
            "reasoning_effort": None,
            "repetition_penalty": 1.05,
            "disable_cache_control": True,
            "keep_tool_result": -1,
            "use_tool_calls": False,
            "oai_tool_thinking": False,
        }
    )

    print("=" * 60)
    print("Testing MiroThinker API")
    print("=" * 60)
    print(f"Base URL: {llm_config.base_url}")
    print(f"Model: {llm_config.model_name}")
    print(f"API Key: {'*' * 10 if llm_config.api_key else 'NOT SET'}")
    print()

    try:
        # Build LLM client
        print("Building LLM client...")
        llm_client = build_llm_client(cfg=llm_config)
        print("✓ LLM client created successfully")
        print()

        # Test message
        test_message = (
            "Hello! Please respond with a simple greeting and tell me what 2+2 equals."
        )
        print(f"Sending test message: {test_message}")
        print()

        # Call API
        print("Calling MiroThinker API...")
        llm_output = await llm_client.create_message(
            message_text=test_message, system_prompt="You are a helpful assistant."
        )

        print("=" * 60)
        print("API Response:")
        print("=" * 60)
        print(f"Response Text: {llm_output.response_text}")
        print()
        print(f"Is Invalid: {llm_output.is_invalid}")
        print(f"Assistant Message: {llm_output.assistant_message}")
        print()

        if llm_output.is_invalid:
            print("❌ API call returned invalid response")
            return False
        else:
            print("✅ API call successful!")
            if llm_output.response_text:
                print(f"✅ Received response: {llm_output.response_text[:200]}...")
            else:
                print("⚠️  Response text is empty")
            return True

    except Exception as e:
        print("=" * 60)
        print("❌ Error occurred:")
        print("=" * 60)
        print(f"Error type: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_mirothinker_api())
    exit(0 if success else 1)
