# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
LLM Module

Contains all LLM client implementations
"""

import os
import importlib
import pkgutil
import inspect

from miroflow.llm.base import (
    LLMClientBase,
    LLMProviderClientBase,
    LLMOutput,
    ContextLimitError,
)
from miroflow.llm.factory import build_llm_client

__all__ = [
    "LLMClientBase",
    "LLMProviderClientBase",  # Backward compatible
    "LLMOutput",
    "ContextLimitError",
    "build_llm_client",
]

# Dynamically import all LLM client classes in the current directory
package_dir = os.path.dirname(__file__)

# Excluded module names
_EXCLUDED_MODULES = {"__init__", "base", "factory", "util"}

for module_info in pkgutil.iter_modules([package_dir]):
    module_name = module_info.name
    if module_name in _EXCLUDED_MODULES:
        continue
    if module_info.ispkg:  # Skip subdirectories (e.g., archived)
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
