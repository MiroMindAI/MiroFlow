# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Tool 工厂模块 - 负责从配置创建 MCP 服务器参数

注意：Tool 不走注册机制，而是通过 MCP 协议动态发现
"""

import sys
from typing import List, Dict, Any, Optional

from mcp import StdioServerParameters
from omegaconf import OmegaConf


def get_mcp_server_configs_from_tool_cfg_paths(cfg_paths: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """
    从工具配置路径列表创建 MCP 服务器配置
    
    Args:
        cfg_paths: 工具配置文件路径列表，如果为None或不存在则返回空列表
    
    Returns:
        MCP 服务器配置列表，每个配置包含 name 和 params
    """
    if cfg_paths is None:
        return []
    
    configs = []

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
            raise RuntimeError(f"Error creating MCP server parameters for tool {config_path}: {e}")

    return configs
