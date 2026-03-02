# # SPDX-FileCopyrightText: 2025 MiromindAI
# #
# # SPDX-License-Identifier: Apache-2.0
#
# NOTE: Skill MCP Server is not yet implemented. The code below is a placeholder
# for future development. Skills are currently loaded and executed directly via
# SkillManager, not through an MCP server. This file is kept as a reference for
# the planned MCP-based skill execution interface.

# import argparse
# import os
# import tempfile
# import aiohttp
# import atexit

# from fastmcp import FastMCP
# from mcp import ClientSession, StdioServerParameters
# from mcp.client.stdio import stdio_client
# import asyncio
# from .utils.smart_request import smart_request

# # Initialize FastMCP server
# mcp = FastMCP("skill-mcp-server")

# @mcp.tool()
# async def expand_markdown(uri: str) -> str:
#     """Read various types of resources (Doc, PPT, PDF, Excel, CSV, ZIP file etc.)
#     described by an file: or data: URI.

#     Args:
#         uri: Required. The URI of the resource to read. Need to start with 'file:' or 'data:' schemes. Files from sandbox are not supported. You should use the local file path.

#     Returns:
#         str: The content of the resource, or an error message if reading fails.
#     """
#     return "Not supported yet"


# if __name__ == "__main__":
#     # Set up argument parser
#     parser = argparse.ArgumentParser(description="Reading MCP Server")
#     parser.add_argument(
#         "--transport",
#         choices=["stdio", "http"],
#         default="stdio",
#         help="Transport method: 'stdio' or 'http' (default: stdio)",
#     )
#     parser.add_argument(
#         "--port",
#         type=int,
#         default=8080,
#         help="Port to use when running with HTTP transport (default: 8080)",
#     )
#     parser.add_argument(
#         "--path",
#         type=str,
#         default="/mcp",
#         help="URL path to use when running with HTTP transport (default: /mcp)",
#     )

#     # Parse command line arguments
#     args = parser.parse_args()

#     # Run the server with the specified transport method
#     if args.transport == "stdio":
#         mcp.run(transport="stdio", show_banner=False)
#     else:
#         # For HTTP transport, include port and path options
#         mcp.run(
#             transport="streamable-http",
#             port=args.port,
#             path=args.path,
#             show_banner=False,
#         )
