#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Test script for jina_scrape_llm_summary tool
Diagnoses issues with the tool including:
- Environment variable configuration
- LLM API connectivity
- Jina scraping functionality
- Full tool workflow
"""

import asyncio
import json
import os
import sys
from pathlib import Path

import httpx

try:
    from dotenv import load_dotenv

    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False
    print(
        "Warning: python-dotenv not installed. Install with: pip install python-dotenv"
    )


def check_environment_variables():
    """Check if all required environment variables are set"""
    print("=" * 80)
    print("Checking Environment Variables")
    print("=" * 80)

    required_vars = {
        "SUMMARY_LLM_BASE_URL": os.environ.get("SUMMARY_LLM_BASE_URL"),
        "SUMMARY_LLM_MODEL_NAME": os.environ.get("SUMMARY_LLM_MODEL_NAME"),
        "SUMMARY_LLM_API_KEY": os.environ.get("SUMMARY_LLM_API_KEY"),
        "JINA_API_KEY": os.environ.get("JINA_API_KEY"),
        "JINA_BASE_URL": os.environ.get("JINA_BASE_URL", "https://r.jina.ai"),
    }

    missing_vars = []
    for var_name, var_value in required_vars.items():
        if var_value:
            # Mask API keys for security
            if "KEY" in var_name:
                display_value = (
                    f"{var_value[:8]}...{var_value[-4:]}"
                    if len(var_value) > 12
                    else "***"
                )
            else:
                display_value = var_value
            print(f"✓ {var_name}: {display_value}")
        else:
            print(f"✗ {var_name}: NOT SET")
            missing_vars.append(var_name)

    if missing_vars:
        print(f"\n⚠️  Missing environment variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✓ All required environment variables are set")
        return True


async def test_llm_api_connection():
    """Test LLM API connectivity"""
    print("\n" + "=" * 80)
    print("Testing LLM API Connection")
    print("=" * 80)

    base_url = os.environ.get("SUMMARY_LLM_BASE_URL", "").strip()
    api_key = os.environ.get("SUMMARY_LLM_API_KEY", "")
    model = os.environ.get("SUMMARY_LLM_MODEL_NAME", "")

    if not base_url:
        print("✗ SUMMARY_LLM_BASE_URL is not set")
        return False

    # Build API URL
    api_url = base_url
    if "/chat/completions" not in api_url:
        if api_url.endswith("/"):
            api_url = api_url.rstrip("/")
        api_url = f"{api_url}/chat/completions"

    print(f"API URL: {api_url}")
    print(f"Model: {model}")

    # Prepare payload
    if "gpt" in model.lower():
        payload = {
            "model": model,
            "max_completion_tokens": 100,
            "messages": [
                {"role": "user", "content": "Say 'Hello' in one word."},
            ],
        }
        if "gpt-5" in model.lower() or "gpt5" in model.lower():
            payload["service_tier"] = "flex"
            payload["reasoning_effort"] = "minimal"
    else:
        payload = {
            "model": model,
            "max_tokens": 100,
            "messages": [
                {"role": "user", "content": "Say 'Hello' in one word."},
            ],
            "temperature": 1.0,
        }

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    try:
        print("\nSending test request...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                api_url,
                headers=headers,
                json=payload,
                timeout=httpx.Timeout(30.0, connect=10.0, read=60.0),
            )

            print(f"Status Code: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0]["message"]["content"]
                        print("✓ API Connection Successful!")
                        print(f"Response: {content[:100]}...")
                        return True
                    else:
                        print(f"✗ Unexpected response format: {data}")
                        return False
                except json.JSONDecodeError as e:
                    print(f"✗ Failed to parse JSON response: {e}")
                    print(f"Raw response: {response.text[:500]}")
                    return False
            elif response.status_code == 503:
                print("✗ 503 Service Unavailable - Server is temporarily unavailable")
                print("This could mean:")
                print("  - The API server is overloaded")
                print("  - The API server is down for maintenance")
                print("  - Rate limiting is too strict")
                print(f"Response: {response.text[:500]}")
                return False
            elif response.status_code == 401:
                print("✗ 401 Unauthorized - API key is invalid or missing")
                return False
            elif response.status_code == 404:
                print("✗ 404 Not Found - API endpoint or model not found")
                return False
            else:
                print(f"✗ HTTP {response.status_code} Error")
                print(f"Response: {response.text[:500]}")
                return False

    except httpx.ConnectTimeout as e:
        print(f"✗ Connection Timeout: {e}")
        print("The API server did not respond in time")
        return False
    except httpx.ConnectError as e:
        print(f"✗ Connection Error: {e}")
        print("Could not connect to the API server")
        return False
    except httpx.ReadTimeout as e:
        print(f"✗ Read Timeout: {e}")
        print("The API server took too long to respond")
        return False
    except httpx.HTTPStatusError as e:
        print(f"✗ HTTP Error: {e}")
        print(f"Status Code: {e.response.status_code}")
        print(f"Response: {e.response.text[:500]}")
        return False
    except Exception as e:
        print(f"✗ Unexpected Error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_jina_scraping():
    """Test Jina scraping functionality"""
    print("\n" + "=" * 80)
    print("Testing Jina Scraping")
    print("=" * 80)

    jina_api_key = os.environ.get("JINA_API_KEY", "")
    jina_base_url = os.environ.get("JINA_BASE_URL", "https://r.jina.ai")

    if not jina_api_key:
        print("⚠️  JINA_API_KEY is not set, skipping Jina test")
        return None

    test_url = "https://www.example.com"
    print(f"Test URL: {test_url}")

    headers = {"Authorization": f"Bearer {jina_api_key}"}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{jina_base_url}/{test_url}",
                headers=headers,
                timeout=httpx.Timeout(30.0),
            )

            if response.status_code == 200:
                print("✓ Jina Scraping Successful!")
                print(f"Content length: {len(response.text)} characters")
                print(f"First 200 chars: {response.text[:200]}...")
                return True
            else:
                print(f"✗ Jina Scraping Failed: HTTP {response.status_code}")
                print(f"Response: {response.text[:500]}")
                return False

    except Exception as e:
        print(f"✗ Jina Scraping Error: {e}")
        return False


async def test_full_tool_workflow():
    """Test the full scrape_and_extract_info workflow"""
    print("\n" + "=" * 80)
    print("Testing Full Tool Workflow")
    print("=" * 80)

    # Import the underlying functions directly
    try:
        from src.tool.mcp_servers.jina_scrape_llm_summary_mcp_server import (
            scrape_url_with_jina,
            extract_info_with_llm,
        )
    except ImportError as e:
        print(f"✗ Failed to import tool functions: {e}")
        return False

    test_url = "https://www.example.com"
    test_question = "What is the main topic of this page?"

    print(f"Test URL: {test_url}")
    print(f"Question: {test_question}")
    print("\nRunning full workflow (scrape + extract)...")

    try:
        # Step 1: Scrape with Jina
        print("\nStep 1: Scraping URL with Jina...")
        scrape_result = await scrape_url_with_jina(test_url, None)

        if not scrape_result.get("success"):
            print(f"✗ Scraping failed: {scrape_result.get('error', 'Unknown error')}")
            return False

        print(
            f"✓ Scraping successful! Content length: {len(scrape_result.get('content', ''))} chars"
        )

        # Step 2: Extract info with LLM
        print("\nStep 2: Extracting information with LLM...")
        extracted_result = await extract_info_with_llm(
            url=test_url,
            content=scrape_result["content"],
            info_to_extract=test_question,
            model=os.environ.get("SUMMARY_LLM_MODEL_NAME", ""),
            max_tokens=8192,
        )

        print("\nResult:")
        print(f"  Success: {extracted_result.get('success', False)}")
        print(f"  Model Used: {extracted_result.get('model_used', 'N/A')}")
        print(f"  Tokens Used: {extracted_result.get('tokens_used', 0)}")

        if extracted_result.get("success"):
            extracted = extracted_result.get("extracted_info", "")
            print(f"  Extracted Info: {extracted[:200]}...")
            print("\n✓ Full workflow test successful!")
            return True
        else:
            error = extracted_result.get("error", "Unknown error")
            print(f"  Error: {error}")
            print("\n✗ Full workflow test failed")
            return False

    except Exception as e:
        print(f"✗ Full workflow test error: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_with_problematic_url():
    """Test with the problematic URL from the logs"""
    print("\n" + "=" * 80)
    print("Testing with Problematic URL from Logs")
    print("=" * 80)

    problematic_url = "https://pmc.ncbi.nlm.nih.gov/articles/PMC6716578/"
    test_question = "What is the main topic of this article?"

    print(f"URL: {problematic_url}")
    print(f"Question: {test_question}")

    try:
        from src.tool.mcp_servers.jina_scrape_llm_summary_mcp_server import (
            scrape_url_with_jina,
            scrape_url_with_python,
            extract_info_with_llm,
        )
    except ImportError as e:
        print(f"✗ Failed to import tool functions: {e}")
        return False

    print("\nRunning full workflow...")
    try:
        # Step 1: Scrape
        print("\nStep 1: Scraping URL...")
        scrape_result = await scrape_url_with_jina(problematic_url, None)

        if not scrape_result.get("success"):
            print("⚠️  Jina scraping failed, trying Python fallback...")
            scrape_result = await scrape_url_with_python(problematic_url, None)

        if not scrape_result.get("success"):
            print(f"✗ Scraping failed: {scrape_result.get('error', 'Unknown error')}")
            return False

        print(
            f"✓ Scraping successful! Content length: {len(scrape_result.get('content', ''))} chars"
        )

        # Step 2: Extract with LLM
        print("\nStep 2: Extracting information with LLM...")
        extracted_result = await extract_info_with_llm(
            url=problematic_url,
            content=scrape_result["content"],
            info_to_extract=test_question,
            model=os.environ.get("SUMMARY_LLM_MODEL_NAME", ""),
            max_tokens=8192,
        )

        print("\nResult:")
        print(f"  Success: {extracted_result.get('success', False)}")

        if extracted_result.get("success"):
            print("✓ Problematic URL test successful!")
            extracted = extracted_result.get("extracted_info", "")
            print(f"  Extracted Info: {extracted[:200]}...")
            return True
        else:
            error = extracted_result.get("error", "Unknown error")
            print(f"  Error: {error}")
            print("\n✗ Problematic URL test failed")
            print("\nDiagnosis:")
            if "503" in error:
                print("  - 503 Service Unavailable error detected")
                print("  - This suggests the LLM API server is overloaded or down")
                print("  - Possible solutions:")
                print("    * Wait and retry later")
                print("    * Use a different LLM API endpoint")
                print("    * Check if the API service is under maintenance")
            elif "Connection" in error:
                print("  - Connection error detected")
                print("  - Check network connectivity and API endpoint URL")
            elif "401" in error or "Unauthorized" in error:
                print("  - Authentication error detected")
                print("  - Check SUMMARY_LLM_API_KEY environment variable")
            return False

    except Exception as e:
        print(f"✗ Test error: {e}")
        import traceback

        traceback.print_exc()
        return False


def load_env_file():
    """Load environment variables from .env file or .envs directory"""
    # Try multiple possible locations
    env_files = [
        Path(".env"),  # Root .env file
        Path(".envs") / ".env",  # .envs/.env
        Path(".envs") / ".env.local",  # .envs/.env.local
        Path("env") / ".env",  # env/.env
        Path("envs") / ".env",  # envs/.env
    ]

    # Also check if .envs is a directory and list files in it
    envs_dir = Path(".envs")
    if envs_dir.exists() and envs_dir.is_dir():
        for env_file in envs_dir.glob("*.env*"):
            if env_file not in env_files:
                env_files.append(env_file)

    loaded = False
    loaded_files = []

    for env_file in env_files:
        if env_file.exists() and env_file.is_file():
            if DOTENV_AVAILABLE:
                load_dotenv(env_file, override=False)
                loaded_files.append(str(env_file))
                loaded = True
            else:
                print(f"⚠️  Found {env_file} but python-dotenv is not installed")
                print("   Install with: pip install python-dotenv")
                print("   Or manually source the .env file before running this script")
                break

    if loaded:
        print(f"✓ Loaded environment variables from: {', '.join(loaded_files)}")
    elif DOTENV_AVAILABLE:
        print("⚠️  No .env file found. Looking for:")
        for env_file in env_files[:5]:  # Show first 5 common paths
            print(f"   - {env_file}")
        print("   Will use system environment variables instead")

    return loaded


async def main():
    """Run all tests"""
    print("\n" + "=" * 80)
    print("Jina Scrape LLM Summary Tool - Diagnostic Test")
    print("=" * 80)

    # Load .env file if available
    print("\nLoading environment variables...")
    load_env_file()

    results = {}

    # Test 1: Environment variables
    results["env_vars"] = check_environment_variables()

    if not results["env_vars"]:
        print("\n⚠️  Some environment variables are missing.")
        print("Please set them before running other tests.")
        print("\nExample:")
        print("  export SUMMARY_LLM_BASE_URL='https://api.miromind.site/v1'")
        print("  export SUMMARY_LLM_MODEL_NAME='openai/gpt-5-nano'")
        print("  export SUMMARY_LLM_API_KEY='your-api-key'")
        print("  export JINA_API_KEY='your-jina-key'")
        return

    # Test 2: LLM API connection
    results["llm_api"] = await test_llm_api_connection()

    # Test 3: Jina scraping
    results["jina"] = await test_jina_scraping()

    # Test 4: Full workflow
    if results["llm_api"]:
        results["full_workflow"] = await test_full_tool_workflow()
    else:
        print("\n⚠️  Skipping full workflow test due to LLM API connection failure")
        results["full_workflow"] = None

    # Test 5: Problematic URL
    if results["llm_api"]:
        results["problematic_url"] = await test_with_problematic_url()
    else:
        print("\n⚠️  Skipping problematic URL test due to LLM API connection failure")
        results["problematic_url"] = None

    # Summary
    print("\n" + "=" * 80)
    print("Test Summary")
    print("=" * 80)

    for test_name, result in results.items():
        if result is True:
            print(f"✓ {test_name}: PASSED")
        elif result is False:
            print(f"✗ {test_name}: FAILED")
        else:
            print(f"⚠️  {test_name}: SKIPPED")

    print("\n" + "=" * 80)

    if all(r for r in results.values() if r is not None):
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed. Please review the output above.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
