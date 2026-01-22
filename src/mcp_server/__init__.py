# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""MiroFlow MCP Server - Main entry point for Forge by MCP integration."""

from .server import mcp, run_server

__all__ = ["mcp", "run_server"]
