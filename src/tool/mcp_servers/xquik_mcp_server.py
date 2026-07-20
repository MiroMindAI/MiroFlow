# SPDX-FileCopyrightText: 2026 MiroMindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import os
from typing import Any

import requests
from fastmcp import FastMCP

from src.logging.logger import setup_mcp_logging


XQUIK_API_KEY = os.environ.get("XQUIK_API_KEY", "")
XQUIK_BASE_URL = os.environ.get("XQUIK_BASE_URL", "https://xquik.com").rstrip("/")
XQUIK_REQUEST_TIMEOUT = float(os.environ.get("XQUIK_REQUEST_TIMEOUT", "30"))

setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("xquik-mcp-server")


def _search_params(
    query: str,
    limit: int,
    query_type: str,
    cursor: str | None = None,
) -> dict[str, Any]:
    normalized_query = query.strip()
    if not normalized_query:
        raise ValueError("query must not be empty")
    if not 1 <= limit <= 200:
        raise ValueError("limit must be between 1 and 200")

    normalized_query_type = query_type.strip().title()
    if normalized_query_type not in {"Latest", "Top"}:
        raise ValueError("query_type must be Latest or Top")

    params = {
        "q": normalized_query,
        "limit": limit,
        "queryType": normalized_query_type,
    }
    if cursor and cursor.strip():
        params["cursor"] = cursor.strip()
    return params


def _request_tweets(
    *,
    api_key: str,
    base_url: str,
    params: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    response = requests.get(
        f"{base_url.rstrip('/')}/api/v1/x/tweets/search",
        headers={"Accept": "application/json", "X-API-Key": api_key},
        params=params,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    if (
        not isinstance(payload, dict)
        or not isinstance(payload.get("tweets"), list)
        or not isinstance(payload.get("has_next_page"), bool)
        or not isinstance(payload.get("next_cursor"), str)
    ):
        raise ValueError("Xquik returned an invalid search response")
    return payload


async def _search_x_tweets(
    query: str,
    limit: int = 20,
    query_type: str = "Latest",
    cursor: str | None = None,
    *,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float | None = None,
) -> str:
    resolved_api_key = XQUIK_API_KEY if api_key is None else api_key
    if not resolved_api_key.strip():
        return "[ERROR]: XQUIK_API_KEY is not set, search_x_tweets is unavailable."

    try:
        params = _search_params(query, limit, query_type, cursor)
        payload = await asyncio.to_thread(
            _request_tweets,
            api_key=resolved_api_key,
            base_url=base_url or XQUIK_BASE_URL,
            params=params,
            timeout=timeout or XQUIK_REQUEST_TIMEOUT,
        )
        return json.dumps(payload, ensure_ascii=False, indent=2)
    except requests.HTTPError as error:
        status = error.response.status_code if error.response is not None else "unknown"
        return f"[ERROR]: Xquik search failed with HTTP status {status}."
    except requests.RequestException:
        return "[ERROR]: Xquik search could not reach the API."
    except (TypeError, ValueError) as error:
        return f"[ERROR]: {error}"


@mcp.tool()
async def search_x_tweets(
    query: str,
    limit: int = 20,
    query_type: str = "Latest",
    cursor: str | None = None,
) -> str:
    """Search X posts through Xquik and return cursor-paginated JSON.

    Args:
        query: X search query, keywords, account filters, or operators.
        limit: Maximum posts to return, from 1 through 200.
        query_type: Latest for chronological results or Top for ranked results.
        cursor: Pagination cursor returned by a previous search.

    Returns:
        JSON containing tweets, has_next_page, and next_cursor.
    """
    return await _search_x_tweets(query, limit, query_type, cursor)


if __name__ == "__main__":
    mcp.run(transport="stdio")
