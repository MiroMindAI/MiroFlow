# SPDX-FileCopyrightText: 2026 MiroMindAI
#
# SPDX-License-Identifier: Apache-2.0

import json
import unittest
from unittest.mock import patch

import requests

from src.tool.mcp_servers.xquik_mcp_server import (
    _search_params,
    _search_x_tweets,
    mcp,
)


class MockResponse:
    def __init__(self, payload, status_code=200):
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self.payload


class SearchParamsTests(unittest.TestCase):
    def test_normalizes_query_type(self):
        self.assertEqual(
            _search_params(" agent tools ", 25, "top", " next-page "),
            {
                "q": "agent tools",
                "limit": 25,
                "queryType": "Top",
                "cursor": "next-page",
            },
        )

    def test_rejects_invalid_limit(self):
        with self.assertRaisesRegex(ValueError, "limit must be between 1 and 200"):
            _search_params("agent tools", 201, "Latest")


class SearchXTweetsTests(unittest.IsolatedAsyncioTestCase):
    async def test_registers_search_tool(self):
        tool = await mcp.get_tool("search_x_tweets")
        self.assertEqual(tool.name, "search_x_tweets")

    @patch("src.tool.mcp_servers.xquik_mcp_server.requests.get")
    async def test_returns_paginated_json(self, get):
        get.return_value = MockResponse(
            {
                "tweets": [{"id": "123", "text": "A source-backed result"}],
                "has_next_page": True,
                "next_cursor": "next-page",
            }
        )

        result = await _search_x_tweets(
            "agent tools",
            30,
            "Top",
            "current-page",
            api_key="test-key",
            base_url="https://example.test/",
            timeout=5,
        )

        self.assertEqual(json.loads(result)["next_cursor"], "next-page")
        get.assert_called_once_with(
            "https://example.test/api/v1/x/tweets/search",
            headers={"Accept": "application/json", "X-API-Key": "test-key"},
            params={
                "q": "agent tools",
                "limit": 30,
                "queryType": "Top",
                "cursor": "current-page",
            },
            timeout=5,
        )

    async def test_requires_api_key(self):
        result = await _search_x_tweets("agent tools", api_key="")
        self.assertEqual(
            result,
            "[ERROR]: XQUIK_API_KEY is not set, search_x_tweets is unavailable.",
        )

    @patch("src.tool.mcp_servers.xquik_mcp_server.requests.get")
    async def test_reports_http_status_without_response_body(self, get):
        get.return_value = MockResponse("private details", status_code=401)

        result = await _search_x_tweets("agent tools", api_key="test-key")

        self.assertEqual(result, "[ERROR]: Xquik search failed with HTTP status 401.")

    @patch("src.tool.mcp_servers.xquik_mcp_server.requests.get")
    async def test_rejects_incomplete_search_response(self, get):
        get.return_value = MockResponse({"tweets": []})

        result = await _search_x_tweets("agent tools", api_key="test-key")

        self.assertEqual(result, "[ERROR]: Xquik returned an invalid search response")


if __name__ == "__main__":
    unittest.main()
