#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.mcp_server.server import run_server

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MiroFlow MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http"],
        default="streamable-http",
        help="Transport method (default: streamable-http)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to use (default: 8000)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="/mcp",
        help="URL path for MCP endpoint (default: /mcp)",
    )

    args = parser.parse_args()

    run_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
        path=args.path,
    )
