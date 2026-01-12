from typing import Union, Dict, Type, Callable, List
from omegaconf import DictConfig, OmegaConf, ListConfig
import importlib
import pkgutil
import threading
from enum import Enum
import os
from src.agents.base_module import BaseAgentModule  # 你 BaseAgentModule 放哪就改哪
from src.logging.task_tracer import get_tracer

logger = get_tracer()

# class Scope(str, Enum):
#     SINGLETON = "singleton"
#     TRANSIENT = "transient"
#     #SCOPED = "scoped"

# def set_scope(scope: Scope):
#     def _decorator(cls):
#         cls.__scope__ = scope
#         return cls
#     return _decorator #TODO

_IMPORTED = False
_LOCK = threading.Lock()
_AGENT_MODULE_REGISTRY: Dict[str, Type[BaseAgentModule]] = {}

def _lazy_import_modules():
    global _IMPORTED
    if _IMPORTED:
        return
    with _LOCK:
        if _IMPORTED:
            return

        pkg = importlib.import_module("src.agents.modules")
        for _, name, _ in pkgutil.iter_modules(pkg.__path__):
            importlib.import_module(f"{pkg.__name__}.{name}")

        _IMPORTED = True

def register_module(name: str) -> Callable[[Type[BaseAgentModule]], Type[BaseAgentModule]]:
    def _decorator(cls: Type[BaseAgentModule]) -> Type[BaseAgentModule]:
        if not issubclass(cls, BaseAgentModule):
            raise TypeError(f"Only subclasses of BaseAgentModule can be registered, got {cls}")
        if name in _AGENT_MODULE_REGISTRY and _AGENT_MODULE_REGISTRY[name] is not cls:
            raise KeyError(f"Duplicate module name '{name}'. "
                           f"Existing: {_AGENT_MODULE_REGISTRY[name]}, New: {cls}")
        _AGENT_MODULE_REGISTRY[name] = cls
        return cls
    return _decorator

def get_registered_modules() -> Dict[str, Type[BaseAgentModule]]:
    """调试用：查看已注册模块"""
    return dict(_AGENT_MODULE_REGISTRY)

def safe_get_module_class(cls_name):
    if cls_name in _AGENT_MODULE_REGISTRY:
        return _AGENT_MODULE_REGISTRY[cls_name]
    else:
        raise KeyError(f"Unknown module class '{cls_name}'")

_RESERVED = {"entrypoint", "global_parameters"}
def build_agent_from_config(cfg: Union[DictConfig, dict]) -> BaseAgentModule:
    #_lazy_import_modules()

    entrypoint = cfg.get("entrypoint", None)
    global_parameters = cfg.get("global_parameters", None)

    return build_agent(cfg[entrypoint])

def build_agent(cfg: Union[DictConfig, dict], sequential = False) -> BaseAgentModule:
    _lazy_import_modules()
    if isinstance(cfg, dict) or isinstance(cfg, list):
        cfg = OmegaConf.create(cfg)
    # if isinstance(cfg, ListConfig) and sequential:
    #     model_class = _AGENT_MODULE_REGISTRY['SequentialAgentModule']
    #     ret = model_class.build(cfg)
    #     return ret
    #print(cfg)
    assert 'type' in cfg, f"Agent module config must have field `type`. \n" + str(cfg)
    module_class = str(cfg['type'])
    if module_class not in _AGENT_MODULE_REGISTRY:
        raise KeyError(f"Unknown module class '{module_class}', "
        f"registered={list(_AGENT_MODULE_REGISTRY.keys())}")
    
    try:
        ret = _AGENT_MODULE_REGISTRY[module_class](cfg = cfg)
    except Exception as e:
        print('------------------')
        print(cfg)
        error_msg = f'Error initializing module {module_class}: {e}, cfg: {cfg}'
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    return ret





