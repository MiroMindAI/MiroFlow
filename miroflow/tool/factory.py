# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Tool factory module - creates MCP server parameters from configuration

Note: Tools are dynamically discovered through the MCP protocol, not the registry
"""

import sys
from typing import List, Dict, Any, Optional

from mcp import StdioServerParameters
from omegaconf import OmegaConf


def get_mcp_server_configs_from_tool_cfg_paths(
    cfg_paths: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """
    Create MCP server configurations from a list of tool config paths.

    Args:
        cfg_paths: List of tool configuration file paths. Returns empty list if None.

    Returns:
        List of MCP server configurations, each containing name and params.
    """
    if cfg_paths is None:
        return []

    configs = []

    # TODO: add support for SSE endpoint
    for config_path in cfg_paths:
        try:
            tool_cfg = OmegaConf.load(config_path)
            configs.append(
                {
                    "name": tool_cfg.get("name"),
                    "params": StdioServerParameters(
                        command=sys.executable
                        if tool_cfg["tool_command"] == "python"
                        else tool_cfg["tool_command"],
                        args=tool_cfg.get("args", []),
                        env=tool_cfg.get("env", {}),
                    ),
                }
            )
        except Exception as e:
            raise RuntimeError(
                f"Error creating MCP server parameters for tool {config_path}: {e}"
            )

    return configs
