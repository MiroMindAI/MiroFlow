# SPDX-FileCopyrightText: 2026 Parallel Web Systems Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Expose the keyless Parallel Search MCP service over MiroFlow's stdio path."""

import os

from fastmcp import FastMCP
from fastmcp.client.transports import StreamableHttpTransport

PARALLEL_SEARCH_URL = "https://search.parallel.ai/mcp"
USER_AGENT = "MiroFlow/0.1.0 (Parallel Search MCP)"


def create_server(url: str = PARALLEL_SEARCH_URL) -> FastMCP:
    """Bridge MCP transports without changing upstream tool schemas or content."""
    # An unset optional CA bundle must use the HTTP client's normal trust store.
    if os.environ.get("SSL_CERT_FILE") == "":
        os.environ.pop("SSL_CERT_FILE")
    transport = StreamableHttpTransport(url, headers={"User-Agent": USER_AGENT})
    return FastMCP.as_proxy(transport, name="tool-searching-parallel")


if __name__ == "__main__":
    create_server().run(transport="stdio")
