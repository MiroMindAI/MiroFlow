# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Unified registration mechanism - only includes code-based components

ComponentType:
  - AGENT: Agent modules
  - IO_PROCESSOR: Input/output processors
  - LLM: LLM clients

Not included:
  - TOOL_SERVER: Discovered dynamically via MCP protocol
  - SKILL: Discovered via filesystem scanning
"""

from typing import Dict, Type, Callable
from enum import Enum
import threading
import importlib
import pkgutil

from miroflow.logging.task_tracer import get_tracer

logger = get_tracer()


class ComponentType(str, Enum):
    AGENT = "agent"
    IO_PROCESSOR = "io_processor"
    LLM = "llm"
    # Note: No TOOL_SERVER and SKILL
    # - TOOL_SERVER: Discovered dynamically via MCP protocol
    # - SKILL: Discovered via filesystem scanning


# Registry: each component type corresponds to a dictionary
_REGISTRIES: Dict[ComponentType, Dict[str, Type]] = {
    ComponentType.AGENT: {},
    ComponentType.IO_PROCESSOR: {},
    ComponentType.LLM: {},
}

# Package path mapping
_PACKAGE_MAP = {
    ComponentType.AGENT: "miroflow.agents",
    ComponentType.IO_PROCESSOR: "miroflow.io_processor",
    ComponentType.LLM: "miroflow.llm",
}

# Import status
_IMPORTED: Dict[ComponentType, bool] = {
    ComponentType.AGENT: False,
    ComponentType.IO_PROCESSOR: False,
    ComponentType.LLM: False,
}

_LOCK = threading.Lock()


def _lazy_import_modules(component_type: ComponentType):
    """Lazy load all modules of the specified type"""
    if _IMPORTED[component_type]:
        return

    with _LOCK:
        if _IMPORTED[component_type]:
            return

        package_name = _PACKAGE_MAP[component_type]
        try:
            pkg = importlib.import_module(package_name)
            for _, name, _ in pkgutil.iter_modules(pkg.__path__):
                if name.startswith("_"):
                    continue
                try:
                    importlib.import_module(f"{package_name}.{name}")
                except ImportError as e:
                    logger.warning(f"Failed to import {package_name}.{name}: {e}")
        except ImportError as e:
            logger.warning(f"Failed to import package {package_name}: {e}")

        _IMPORTED[component_type] = True


def register(component_type: ComponentType, name: str) -> Callable[[Type], Type]:
    """
    Decorator to register a component

    Usage:
        @register(ComponentType.AGENT, "IterativeAgentWithToolAndRollback")
        class IterativeAgentWithToolAndRollback(BaseAgent):
            ...
    """

    def _decorator(cls: Type) -> Type:
        registry = _REGISTRIES[component_type]
        if name in registry and registry[name] is not cls:
            raise KeyError(
                f"Duplicate {component_type.value} name '{name}'. "
                f"Existing: {registry[name]}, New: {cls}"
            )
        registry[name] = cls
        return cls

    return _decorator


def get_registered_components(component_type: ComponentType) -> Dict[str, Type]:
    """Get all registered components of the specified type (for debugging)"""
    _lazy_import_modules(component_type)
    return dict(_REGISTRIES[component_type])


def get_component_class(component_type: ComponentType, name: str) -> Type:
    """Get the component class by type and name"""
    _lazy_import_modules(component_type)
    registry = _REGISTRIES[component_type]
    if name not in registry:
        raise KeyError(
            f"Unknown {component_type.value} '{name}', "
            f"registered={list(registry.keys())}"
        )
    return registry[name]


# ==================== Legacy API Compatibility ====================


def register_module(name: str) -> Callable[[Type], Type]:
    """
    Backward compatible register_module API
    Automatically detects component type and registers
    """

    def _decorator(cls: Type) -> Type:
        # Infer component type from class name or module path
        module_path = cls.__module__

        if "io_processor" in module_path:
            component_type = ComponentType.IO_PROCESSOR
        elif "agents" in module_path:
            component_type = ComponentType.AGENT
        elif "llm" in module_path:
            component_type = ComponentType.LLM
        else:
            # Default to AGENT
            component_type = ComponentType.AGENT

        return register(component_type, name)(cls)

    return _decorator


# Expose old function names for backward compatibility
_AGENT_MODULE_REGISTRY = _REGISTRIES[ComponentType.AGENT]


def get_registered_modules() -> Dict[str, Type]:
    """Legacy API: Get registered agent modules"""
    _lazy_import_modules(ComponentType.AGENT)
    _lazy_import_modules(ComponentType.IO_PROCESSOR)
    # Merge AGENT and IO_PROCESSOR registries (old behavior)
    merged = {}
    merged.update(_REGISTRIES[ComponentType.AGENT])
    merged.update(_REGISTRIES[ComponentType.IO_PROCESSOR])
    return merged


def safe_get_module_class(cls_name: str) -> Type:
    """Legacy API: Safely get module class"""
    modules = get_registered_modules()
    if cls_name in modules:
        return modules[cls_name]
    else:
        raise KeyError(f"Unknown module class '{cls_name}'")
