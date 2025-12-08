# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import requests
import asyncio
import json
from mcp import (
    ClientSession,
    StdioServerParameters,
    stdio_client,
)  # (already imported in config.py)
import urllib.parse
from markitdown import MarkItDown
import io


def request_to_json(content: str) -> dict:
    if isinstance(content, str) and "Markdown Content:\n" in content:
        # If the content starts with "Markdown Content:\n", extract only the part after it (from JINA)
        content = content.split("Markdown Content:\n")[1]
    return json.loads(content)


async def smart_request(url: str, params: dict = None, env: dict = None) -> str:
    # Handle empty URL
    if not url:
        return {
            "text": f"[ERROR]: Invalid URL: '{url}'. URL cannot be empty.",
            "usage": {},
        }

    if env:
        JINA_API_KEY = env.get("JINA_API_KEY", "")
        SERPER_API_KEY = env.get("SERPER_API_KEY", "")
        JINA_BASE_URL = env.get("JINA_BASE_URL", "https://r.jina.ai")
    else:
        JINA_API_KEY = ""
        SERPER_API_KEY = ""

    if JINA_API_KEY == "" and SERPER_API_KEY == "":
        return {
            "text": "[ERROR]: JINA_API_KEY and SERPER_API_KEY are not set, smart_request is not available.",
            "usage": {},
        }

    IS_MIRO_API = True if "miro" in JINA_BASE_URL else False

    # Auto-add https:// if no protocol is specified
    protocol_hint = ""
    if not url.startswith(("http://", "https://")):
        original_url = url
        url = f"https://{url}"
        protocol_hint = f"[NOTE]: Automatically added 'https://' to URL '{original_url}' -> '{url}'\n\n"

    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    # Check for restricted domains
    if "huggingface.co/datasets" in url or "huggingface.co/spaces" in url:
        return {
            "text": "You are trying to scrape a Hugging Face dataset for answers, please do not use the scrape tool for this purpose.",
            "usage": {},
        }

    retry_count = 0
    max_retries = 3

    while retry_count < max_retries:
        try:
            error_msg = "[NOTE]: If the link is a file / image / video / audio, please use other applicable tools, or try to process it in the sandbox.\n"
            youtube_hint = ""
            if (
                "youtube.com/watch" in url
                or "youtube.com/shorts" in url
                or "youtube.com/live" in url
            ):
                youtube_hint = "[NOTE]: If you need to get information about its visual or audio content, please use tool 'visual_audio_youtube_analyzing' instead. This tool may not be able to provide visual and audio content of a YouTube Video.\n\n"

            jina_response = await scrape_jina(url, JINA_API_KEY, JINA_BASE_URL)
            content = jina_response.get("text", None)
            jina_err = jina_response.get("error", None)
            jina_usage = jina_response.get("usage", {})
            if jina_err:
                error_msg += f"Failed to get content from Jina.ai: {jina_err}\n"
            elif content is None or content.strip() == "":
                error_msg += "No content got from Jina.ai.\n"
            else:
                return {
                    "text": protocol_hint + youtube_hint + content,
                    "usage": jina_usage,
                }

            if not IS_MIRO_API:
                # Try Serper API for scraping if not using Miro API
                # (Miro API does not support caching Serper scraping results)
                serper_response = await scrape_serper(url, SERPER_API_KEY)
                content = serper_response.get("text", None)
                serper_err = serper_response.get("error", None)
                serper_usage = serper_response.get("usage", {})
                if serper_err:
                    error_msg += f"Failed to get content from SERPER: {serper_err}\n"
                elif content is None or content.strip() == "":
                    error_msg += "No content got from SERPER.\n"
                else:
                    return {
                        "text": protocol_hint + youtube_hint + content,
                        "usage": serper_usage,
                    }

            content, request_err = scrape_request(url)
            if request_err:
                error_msg += f"Failed to get content from requests: {request_err}\n"
            elif content is None or content.strip() == "":
                error_msg += "No content got from requests.\n"
            else:
                return {"text": protocol_hint + youtube_hint + content, "usage": {}}

            raise Exception(error_msg)

        except Exception as e:
            retry_count += 1
            if retry_count >= max_retries:
                return {"text": f"[ERROR]: {str(e)}", "usage": {}}
            else:
                await asyncio.sleep(4**retry_count)


async def scrape_jina(url: str, jina_api_key: str, jina_base_url: str) -> dict:
    # Use Jina.ai reader API to convert URL to LLM-friendly text
    if jina_api_key == "":
        return {
            "text": None,
            "error": "JINA_API_KEY is not set, JINA scraping is not available.",
            "usage": {},
        }

    jina_headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {jina_api_key}",
        "X-Base": "final",
        "X-Engine": "browser",
        "X-With-Generated-Alt": "true",
        "X-With-Iframe": "true",
        "X-With-Shadow-Dom": "true",
    }

    jina_url = f"{jina_base_url}/{url}"
    try:
        response = requests.get(jina_url, headers=jina_headers, timeout=120)
        if response.status_code == 422:
            # Return as error to allow fallback to other tools and retries
            return {
                "text": None,
                "error": "Tool execution failed with Jina 422 error, which may indicate the URL is a file. This tool does not support files. If you believe the URL might point to a file, you should try using other applicable tools, or try to process it in the sandbox.",
                "usage": {},
            }
        response.raise_for_status()
        content = response.json().get("data", {}).get("content", "")
        if (
            "Warning: This page maybe not yet fully loaded, consider explicitly specify a timeout."
            in content
        ):
            # Try with longer timeout
            response = requests.get(jina_url, headers=jina_headers, timeout=300)
            if response.status_code == 422:
                return {
                    "text": None,
                    "error": "Tool execution failed with Jina 422 error, which may indicate the URL is a file. This tool does not support files. If you believe the URL might point to a file, you should try using other applicable tools, or try to process it in the sandbox.",
                    "usage": {},
                }
            response.raise_for_status()
            content = response.json().get("data", {}).get("content", "")
        return {
            "text": content,
            "error": None,
            "usage": {
                "JINA": response.json()
                .get("meta", {})
                .get("usage", {})
                .get("tokens", 0)
            },
        }
    except Exception as e:
        return {
            "text": None,
            "error": f"Failed to get content from Jina.ai: {str(e)}\n",
            "usage": {},
        }


async def scrape_serper(url: str, serper_api_key: str) -> dict:
    """This function uses SERPER for scraping a website.
    Args:
        url: The URL of the website to scrape.
    """
    if serper_api_key == "":
        return {
            "text": None,
            "error": "SERPER_API_KEY is not set, SERPER scraping is not available.",
            "usage": {},
        }

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "serper-search-scrape-mcp-server"],
        env={"SERPER_API_KEY": serper_api_key},
    )
    tool_name = "scrape"
    arguments = {"url": url}
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=None) as session:
                await session.initialize()
                tool_result = await session.call_tool(tool_name, arguments=arguments)
                result_content = (
                    tool_result.content[-1].text if tool_result.content else ""
                )
        return {"text": result_content, "error": None, "usage": {"SERPER": 1}}
    except Exception as e:
        return {"text": None, "error": f"Tool execution failed: {str(e)}", "usage": {}}


def scrape_request(url: str) -> tuple[str, str]:
    """This function uses requests to scrape a website.
    Args:
        url: The URL of the website to scrape.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        try:
            stream = io.BytesIO(response.content)
            md = MarkItDown()
            content = md.convert_stream(stream).text_content
            return content, None
        except Exception:
            # If MarkItDown conversion fails, return raw response text
            return response.text, None

    except Exception as e:
        return None, f"{str(e)}"
