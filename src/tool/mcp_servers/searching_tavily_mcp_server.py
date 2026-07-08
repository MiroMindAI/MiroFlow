# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import json
from fastmcp import FastMCP
from tavily import TavilyClient
from src.logging.logger import setup_mcp_logging


TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

# Initialize FastMCP server
setup_mcp_logging(tool_name=os.path.basename(__file__))
mcp = FastMCP("searching-tavily-mcp-server")


@mcp.tool()
async def tavily_search(
    query: str,
    max_results: int = 10,
    search_depth: str = "advanced",
    topic: str = "general",
    time_range: str = None,
    include_domains: list[str] = None,
    exclude_domains: list[str] = None,
) -> str:
    """Perform web searches via the Tavily API and retrieve relevant results.

    Args:
        query: Search query string (keep under 400 characters for best results).
        max_results: The number of results to return (default: 10).
        search_depth: Search depth - 'basic' for quick results or 'advanced' for highest relevance (default: 'advanced').
        topic: Search topic category - 'general', 'news', or 'finance' (default: 'general').
        time_range: Time filter for results - 'day', 'week', 'month', 'year', or None for no filter.
        include_domains: List of domains to restrict search to (e.g. ['example.com']).
        exclude_domains: List of domains to exclude from search.

    Returns:
        The search results as a JSON string.
    """
    if not TAVILY_API_KEY:
        return "[ERROR]: TAVILY_API_KEY is not set, tavily_search tool is not available."

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        kwargs = {
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "topic": topic,
        }
        if time_range:
            kwargs["time_range"] = time_range
        if include_domains:
            kwargs["include_domains"] = include_domains
        if exclude_domains:
            kwargs["exclude_domains"] = exclude_domains

        response = client.search(**kwargs)
        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        return f"[ERROR]: tavily_search tool execution failed: {str(e)}"


@mcp.tool()
async def scrape_website(url: str) -> str:
    """Scrape a website for its content using Tavily's extract API.

    This tool extracts the main content from a given URL. It can be used to get
    webpage content, article text, documentation pages, etc.

    Args:
        url: The URL of the website to scrape.

    Returns:
        The scraped website content.
    """
    if not TAVILY_API_KEY:
        return "[ERROR]: TAVILY_API_KEY is not set, scrape_website tool is not available."

    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        response = client.extract(urls=[url])

        if response.get("results"):
            result = response["results"][0]
            return result.get("raw_content", result.get("text", ""))
        elif response.get("failed_results"):
            failed = response["failed_results"][0]
            return f"[ERROR]: Failed to extract content from {url}: {failed.get('error', 'Unknown error')}"
        else:
            return f"[ERROR]: No content extracted from {url}"

    except Exception as e:
        return f"[ERROR]: scrape_website tool execution failed: {str(e)}"


if __name__ == "__main__":
    mcp.run(transport="stdio", show_banner=False)
