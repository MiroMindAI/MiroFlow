# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
LLM 模块

包含所有 LLM 客户端实现
"""

import os
import importlib
import pkgutil
import inspect

from src.llm.base import LLMClientBase, LLMProviderClientBase, LLMOutput
from src.llm.factory import build_llm_client

__all__ = [
    "LLMClientBase",
    "LLMProviderClientBase",  # 向后兼容
    "LLMOutput",
    "build_llm_client",
]

# 动态导入当前目录下所有 LLM 客户端类
package_dir = os.path.dirname(__file__)

# 排除的模块名
_EXCLUDED_MODULES = {"__init__", "base", "factory", "util"}

for module_info in pkgutil.iter_modules([package_dir]):
    module_name = module_info.name
    if module_name in _EXCLUDED_MODULES:
        continue
    if module_info.ispkg:  # 跳过子目录（如 archived）
        continue
    
    try:
        # Import the module
        module = importlib.import_module(f"{__name__}.{module_name}")
        # Inspect all classes defined in the module
        for name, obj in inspect.getmembers(module, inspect.isclass):
            # Only include classes defined in this module (not imported ones)
            if obj.__module__ == module.__name__:
                globals()[name] = obj
                __all__.append(name)
    except ImportError:
        pass  # Skip modules that fail to import
