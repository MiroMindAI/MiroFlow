# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Tool 模块

注意：Tool 不走注册机制，而是通过 MCP 协议动态发现
"""

from src.tool.manager import ToolManager
from src.tool.factory import get_mcp_server_configs_from_tool_cfg_paths

__all__ = [
    "ToolManager",
    "get_mcp_server_configs_from_tool_cfg_paths",
]
