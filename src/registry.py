# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
统一注册机制 - 只包含代码类组件

ComponentType:
  - AGENT: Agent 模块
  - IO_PROCESSOR: 输入/输出处理器
  - LLM: LLM 客户端

不包含:
  - TOOL_SERVER: 通过 MCP 协议动态发现
  - SKILL: 通过文件系统扫描发现
"""

from typing import Dict, Type, Callable
from enum import Enum
import threading
import importlib
import pkgutil

from src.logging.task_tracer import get_tracer

logger = get_tracer()


class ComponentType(str, Enum):
    AGENT = "agent"
    IO_PROCESSOR = "io_processor"
    LLM = "llm"
    # 注意：没有 TOOL_SERVER 和 SKILL
    # - TOOL_SERVER: 通过 MCP 协议动态发现
    # - SKILL: 通过文件系统扫描发现


# 注册表：每种组件类型对应一个字典
_REGISTRIES: Dict[ComponentType, Dict[str, Type]] = {
    ComponentType.AGENT: {},
    ComponentType.IO_PROCESSOR: {},
    ComponentType.LLM: {},
}

# 包路径映射
_PACKAGE_MAP = {
    ComponentType.AGENT: "src.agents",
    ComponentType.IO_PROCESSOR: "src.io_processor",
    ComponentType.LLM: "src.llm",
}

# 导入状态
_IMPORTED: Dict[ComponentType, bool] = {
    ComponentType.AGENT: False,
    ComponentType.IO_PROCESSOR: False,
    ComponentType.LLM: False,
}

_LOCK = threading.Lock()


def _lazy_import_modules(component_type: ComponentType):
    """懒加载指定类型的所有模块"""
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
    注册组件的装饰器
    
    Usage:
        @register(ComponentType.AGENT, "IterativeAgentWithTool")
        class IterativeAgentWithTool(BaseAgent):
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
    """获取指定类型的所有已注册组件（调试用）"""
    _lazy_import_modules(component_type)
    return dict(_REGISTRIES[component_type])


def get_component_class(component_type: ComponentType, name: str) -> Type:
    """获取指定类型和名称的组件类"""
    _lazy_import_modules(component_type)
    registry = _REGISTRIES[component_type]
    if name not in registry:
        raise KeyError(
            f"Unknown {component_type.value} '{name}', "
            f"registered={list(registry.keys())}"
        )
    return registry[name]


# ==================== 兼容旧 API ====================

def register_module(name: str) -> Callable[[Type], Type]:
    """
    兼容旧的 register_module API
    自动检测组件类型并注册
    """
    def _decorator(cls: Type) -> Type:
        # 根据类名或模块路径推断组件类型
        module_path = cls.__module__
        
        if "io_processor" in module_path:
            component_type = ComponentType.IO_PROCESSOR
        elif "agents" in module_path:
            component_type = ComponentType.AGENT
        elif "llm" in module_path:
            component_type = ComponentType.LLM
        else:
            # 默认作为 AGENT
            component_type = ComponentType.AGENT
        
        return register(component_type, name)(cls)
    return _decorator


# 暴露旧的函数名以保持兼容性
_AGENT_MODULE_REGISTRY = _REGISTRIES[ComponentType.AGENT]


def get_registered_modules() -> Dict[str, Type]:
    """兼容旧 API：获取已注册的 agent 模块"""
    _lazy_import_modules(ComponentType.AGENT)
    _lazy_import_modules(ComponentType.IO_PROCESSOR)
    # 合并 AGENT 和 IO_PROCESSOR 注册表（旧行为）
    merged = {}
    merged.update(_REGISTRIES[ComponentType.AGENT])
    merged.update(_REGISTRIES[ComponentType.IO_PROCESSOR])
    return merged


def safe_get_module_class(cls_name: str) -> Type:
    """兼容旧 API：安全获取模块类"""
    modules = get_registered_modules()
    if cls_name in modules:
        return modules[cls_name]
    else:
        raise KeyError(f"Unknown module class '{cls_name}'")
