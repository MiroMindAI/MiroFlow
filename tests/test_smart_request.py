# SPDX-FileCopyrightText: 2026 MiroMindAI
#
# SPDX-License-Identifier: Apache-2.0

import unittest
from unittest.mock import Mock, patch

from src.tool.mcp_servers.utils.smart_request import (
    REQUEST_TIMEOUT_SECONDS,
    scrape_request,
)


class ScrapeRequestTests(unittest.TestCase):
    @patch("src.tool.mcp_servers.utils.smart_request.MarkItDown")
    @patch("src.tool.mcp_servers.utils.smart_request.requests.get")
    def test_bounds_direct_requests(self, get, markitdown):
        response = Mock()
        response.content = b"<h1>Example</h1>"
        response.raise_for_status.return_value = None
        get.return_value = response
        markitdown.return_value.convert_stream.return_value.text_content = "Example"

        content, error = scrape_request("https://example.test")

        self.assertEqual((content, error), ("Example", None))
        get.assert_called_once_with(
            "https://example.test",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                )
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    @patch("src.tool.mcp_servers.utils.smart_request.requests.get")
    def test_allows_timeout_override(self, get):
        get.side_effect = TimeoutError("request timed out")

        content, error = scrape_request("https://example.test", timeout=5)

        self.assertIsNone(content)
        self.assertEqual(error, "request timed out")
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["timeout"], 5)


if __name__ == "__main__":
    unittest.main()
