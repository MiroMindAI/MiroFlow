# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import itertools
import json
import logging
import os
import re
from typing import Any, Dict
from urllib.parse import urldefrag, urlparse

import httpx
from fastmcp import FastMCP
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)
from tencentcloud.common import credential
from tencentcloud.common.exception.tencent_cloud_sdk_exception import (
    TencentCloudSDKException,
)
from tencentcloud.common.profile.client_profile import ClientProfile
from tencentcloud.common.profile.http_profile import HttpProfile
from tencentcloud.wsa.v20250508 import models as wsa_models
from tencentcloud.wsa.v20250508 import wsa_client

from .utils.url_unquote import decode_http_urls_in_dict

# Configure logging
logger = logging.getLogger("miroflow")

SERPER_BASE_URL = os.getenv("SERPER_BASE_URL", "https://google.serper.dev")
SERPER_API_KEY = os.getenv("SERPER_API_KEY", "")

TENCENTCLOUD_SECRET_ID = os.getenv("TENCENTCLOUD_SECRET_ID", "")
TENCENTCLOUD_SECRET_KEY = os.getenv("TENCENTCLOUD_SECRET_KEY", "")

# Concurrency limiter for Sogou API to avoid RequestLimitExceeded errors
_sogou_semaphore: asyncio.Semaphore | None = None


def _get_sogou_semaphore() -> asyncio.Semaphore:
    """Lazily initialize the semaphore in the current event loop."""
    global _sogou_semaphore
    if _sogou_semaphore is None:
        _sogou_semaphore = asyncio.Semaphore(10)
    return _sogou_semaphore


# Initialize FastMCP server
mcp = FastMCP("tool-serper-sogou-search")


def _contains_chinese(text: str) -> bool:
    """Check if text contains Chinese characters."""
    return bool(re.search(r"[\u4e00-\u9fff]", text))


def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication (strip fragment, trailing slash, lowercase host)."""
    if not url:
        return ""
    url_no_frag, _ = urldefrag(url)
    parsed = urlparse(url_no_frag)
    path = parsed.path.rstrip("/") or "/"
    normalized = f"{parsed.scheme}://{parsed.netloc.lower()}{path}"
    if parsed.query:
        normalized += f"?{parsed.query}"
    return normalized


def _clean_sogou_query(query: str) -> str:
    """Create a Sogou-friendly query variant by removing quotes and special chars."""
    cleaned = query.replace('"', "").replace('"', "").replace('"', "")
    cleaned = cleaned.replace("「", "").replace("」", "")
    return cleaned.strip()


def _dedup_and_interleave(serper_results: list, sogou_results: list) -> list:
    """Deduplicate by URL and interleave results from two engines."""
    seen_urls = set()
    combined = []
    for item in itertools.chain.from_iterable(
        itertools.zip_longest(serper_results, sogou_results)
    ):
        if item is None:
            continue
        normalized = _normalize_url(item.get("link", ""))
        if normalized and normalized in seen_urls:
            continue
        if normalized:
            seen_urls.add(normalized)
        combined.append(item)
    return combined


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(
        (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError)
    ),
)
async def make_serper_request(
    payload: Dict[str, Any], headers: Dict[str, str]
) -> httpx.Response:
    """Make HTTP request to Serper API with retry logic."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{SERPER_BASE_URL}/search",
            json=payload,
            headers=headers,
        )
        response.raise_for_status()
        return response


def _is_huggingface_dataset_or_space_url(url):
    """
    Check if the URL is a HuggingFace dataset or space URL.
    :param url: The URL to check
    :return: True if it's a HuggingFace dataset or space URL, False otherwise
    """
    if not url:
        return False
    return "huggingface.co/datasets" in url or "huggingface.co/spaces" in url


def _sogou_search_sync(query: str, num_results: int = 10) -> list:
    """
    Perform Sogou/web search via TencentCloud WSA (Web Search API).
    Uses the SearchPro action at wsa.tencentcloudapi.com.
    Returns a list of organic results in the same format as Serper.
    """
    if not TENCENTCLOUD_SECRET_ID or not TENCENTCLOUD_SECRET_KEY:
        logger.warning("TencentCloud credentials not set, skipping Sogou search")
        return []

    try:
        cred = credential.Credential(TENCENTCLOUD_SECRET_ID, TENCENTCLOUD_SECRET_KEY)
        httpProfile = HttpProfile()
        httpProfile.endpoint = "wsa.tencentcloudapi.com"
        clientProfile = ClientProfile()
        clientProfile.httpProfile = httpProfile

        client = wsa_client.WsaClient(cred, "", clientProfile)

        req = wsa_models.SearchProRequest()
        req.Query = query

        resp = client.SearchPro(req)

        # Pages is a list of JSON strings, each representing one search result
        # Fields per page: title, date, url, passage, content, site, score, images, favicon
        organic_results = []
        pages_list = resp.Pages or []

        for page_json_str in pages_list[:num_results]:
            try:
                item = json.loads(page_json_str)
            except (json.JSONDecodeError, TypeError):
                continue

            result = {
                "title": item.get("title", ""),
                "link": item.get("url", ""),
                "snippet": item.get("passage", "") or item.get("content", ""),
                "source": "sogou",
            }
            if item.get("date"):
                result["date"] = item["date"]
            if item.get("site"):
                result["siteName"] = item["site"]

            if result["link"] and not _is_huggingface_dataset_or_space_url(
                result["link"]
            ):
                organic_results.append(result)

        return organic_results

    except TencentCloudSDKException as e:
        logger.error(f"Sogou search TencentCloud SDK error: {e}")
        return []
    except Exception as e:
        logger.error(f"Sogou search unexpected error: {e}")
        return []


async def _sogou_search_async(query: str, num_results: int = 10) -> list:
    """Async wrapper for Sogou search with concurrency limiting and query cleaning."""
    # Use a cleaned query variant for Sogou to improve complementarity with Google
    cleaned_query = _clean_sogou_query(query)
    if not cleaned_query:
        cleaned_query = query.strip()
    async with _get_sogou_semaphore():
        return await asyncio.to_thread(_sogou_search_sync, cleaned_query, num_results)


async def _serper_search(
    q: str,
    gl: str = "us",
    hl: str = "en",
    location: str = None,
    num: int = None,
    tbs: str = None,
    page: int = None,
    autocorrect: bool = None,
) -> tuple[list, dict]:
    """Perform a Serper search and return (organic_results, search_params)."""

    async def perform_search(search_query: str) -> tuple[list, dict]:
        payload: dict[str, Any] = {
            "q": search_query.strip(),
            "gl": gl,
            "hl": hl,
        }

        if location:
            payload["location"] = location
        if num is not None:
            payload["num"] = num
        else:
            payload["num"] = 10
        if tbs:
            payload["tbs"] = tbs
        if page is not None:
            payload["page"] = page
        if autocorrect is not None:
            payload["autocorrect"] = autocorrect

        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json",
        }

        response = await make_serper_request(payload, headers)
        data = response.json()

        organic_results = []
        if "organic" in data:
            for item in data["organic"]:
                if _is_huggingface_dataset_or_space_url(item.get("link", "")):
                    continue
                organic_results.append(item)

        return organic_results, data.get("searchParameters", {})

    original_query = q.strip()
    organic_results, search_params = await perform_search(original_query)

    # If no results and query contains quotes, retry without quotes
    if not organic_results and '"' in original_query:
        query_without_quotes = original_query.replace('"', "").strip()
        if query_without_quotes:
            organic_results, search_params = await perform_search(query_without_quotes)

    return organic_results, search_params


@mcp.tool()
async def google_search(
    q: str,
    gl: str = "us",
    hl: str = "en",
    location: str = None,
    num: int = None,
    tbs: str = None,
    page: int = None,
    autocorrect: bool = None,
):
    """
    Tool to perform web searches and retrieve rich results.

    When the search query contains Chinese characters, this tool first performs
    a Sogou search (optimized for Chinese content), then a Google search via
    Serper API, and concatenates the results. For non-Chinese queries, it uses
    only Serper/Google search.

    Args:
        q: Search query string
        gl: Optional region code for search results in ISO 3166-1 alpha-2 format (e.g., 'us')
        hl: Optional language code for search results in ISO 639-1 format (e.g., 'en')
        location: Optional location for search results (e.g., 'SoHo, New York, United States', 'California, United States')
        num: Number of results to return (default: 10)
        tbs: Time-based search filter ('qdr:h' for past hour, 'qdr:d' for past day, 'qdr:w' for past week, 'qdr:m' for past month, 'qdr:y' for past year)
        page: Page number of results to return (default: 1)
        autocorrect: Whether to autocorrect spelling in query

    Returns:
        Dictionary containing search results and metadata.
    """
    # Check for Serper API key
    if not SERPER_API_KEY:
        return json.dumps(
            {
                "success": False,
                "error": "SERPER_API_KEY environment variable not set",
                "results": [],
            },
            ensure_ascii=False,
        )

    # Validate required parameter
    if not q or not q.strip():
        return json.dumps(
            {
                "success": False,
                "error": "Search query 'q' is required and cannot be empty",
                "results": [],
            },
            ensure_ascii=False,
        )

    try:
        query_has_chinese = _contains_chinese(q)

        if query_has_chinese:
            # Chinese query: run Sogou and Serper in parallel, then dedup and interleave
            logger.info(f"Chinese detected in query, using Sogou + Serper: {q[:50]}...")

            num_results = num if num is not None else 10

            # Run both searches in parallel
            sogou_task = asyncio.create_task(
                _sogou_search_async(q.strip(), num_results)
            )
            serper_task = asyncio.create_task(
                _serper_search(
                    q,
                    gl=gl,
                    hl=hl,
                    location=location,
                    num=num,
                    tbs=tbs,
                    page=page,
                    autocorrect=autocorrect,
                )
            )
            sogou_results, (serper_results, search_params) = await asyncio.gather(
                sogou_task, serper_task
            )

            # Deduplicate by URL and interleave (Google first, Sogou second)
            combined_organic = _dedup_and_interleave(serper_results, sogou_results)

            response_data = {
                "organic": combined_organic,
                "searchParameters": search_params,
                "search_engines_used": ["sogou", "serper"],
            }
        else:
            # Non-Chinese query: Serper only
            serper_results, search_params = await _serper_search(
                q,
                gl=gl,
                hl=hl,
                location=location,
                num=num,
                tbs=tbs,
                page=page,
                autocorrect=autocorrect,
            )

            response_data = {
                "organic": serper_results,
                "searchParameters": search_params,
                "search_engines_used": ["serper"],
            }

        response_data = decode_http_urls_in_dict(response_data)

        return json.dumps(response_data, ensure_ascii=False)

    except Exception as e:
        return json.dumps(
            {
                "success": False,
                "error": f"Unexpected error: {str(e)}",
                "results": [],
            },
            ensure_ascii=False,
        )


if __name__ == "__main__":
    mcp.run(show_banner=False)
