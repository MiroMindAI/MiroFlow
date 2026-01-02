from typing import Union, Dict, Type, Callable, List
from omegaconf import DictConfig, OmegaConf, ListConfig
import importlib
import pkgutil
import threading
from enum import Enum
import os
from src.agents.base_module import BaseAgentModule  # 你 BaseAgentModule 放哪就改哪
from src.logging.logger import setup_logger

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = setup_logger(level=LOGGER_LEVEL)

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

    # if isinstance(cfg, dict):
    #     cfg = OmegaConf.create(cfg)

    # if "entrypoint" not in cfg:
    #     raise KeyError(f"Agent module config must have field `entrypoint`. \n" + str(cfg))

    # #global_parameters = 

    # if isinstance(cfg, (list, ListConfig)): #Sequential
    #     modules: List[BaseAgentModule] = [build_agent(c, **kwargs) for c in list(cfg)]
    #     seq_cls = _AGENT_MODULE_REGISTRY["SequentialAgentModule"]
    #     seq_cfg = OmegaConf.create({"type": "SequentialAgentModule", "modules": modules})
    #     return seq_cls.build(seq_cfg, modules=modules, **kwargs)

    # if "type" not in cfg:
    #    raise KeyError("Agent module config must have field `type`\n" + str(cfg))
       
    # module_class = str(cfg['type'])

    # if module_class not in _AGENT_MODULE_REGISTRY:
    #     raise KeyError(
    #         f"Unknown module class '{module_class}', "
    #         f"registered={list(_AGENT_MODULE_REGISTRY.keys())}"
    #     )

    # return _AGENT_MODULE_REGISTRY[module_class].build(cfg, **kwargs)

# from typing import Union, Any, Dict
# from omegaconf import DictConfig, OmegaConf
# from omegaconf.listconfig import ListConfig


# _RESERVED = {"entrypoint", "global_parameters"}
# _COMPONENTS = {'llm', 'tools', 'prompt'}

# def build_agent(cfg: Union[DictConfig, dict], **kwargs):
#     """
#     新语义：
#     - 只有顶层 definitions（cfg 的一级 key）且带 `type` 的，才会被实例化为模块
#     - 传播参数：由模块类属性 PROPAGATE_PARAMETERS 指定（例如 ("llm","prompt","tool")）
#     - 构建 entrypoint 时，父模块的传播参数会作为默认向子模块递归传递；子模块可覆写
#     """
#     _lazy_import_modules()
#     if isinstance(cfg, dict):
#         cfg = OmegaConf.create(cfg)

#     #if "entrypoint" not in cfg:
#     #     raise KeyError("Top config must have field `entrypoint`")

#     defs = {k: cfg[k] for k in cfg.keys() if k not in _RESERVED}
#     id2name = {id(v): k for k, v in defs.items()}

#     global_parameters = cfg.get("global_parameters", None)
#     if global_parameters is None:
#         global_parameters = {}

#     def _is_top_module_ref(name, cfg: DictConfig) -> bool:
#         return "type" in cfg


#     def _instantiate_top_module(name: str, parent_modules: Dict[str, Any]):
#         """
#         node_cfg 是某个顶层模块定义（带 type）
#         parent_env 是父模块传播下来的默认参数（如 llm/prompt/tool 的“实例/配置”）
#         """
#         module_config = cfg[name]
#         module_type = str(module_config["type"])

#         if module_type not in _AGENT_MODULE_REGISTRY:
#             raise KeyError(
#                 f"Unknown module type '{module_type}', "
#                 f"registered={list(_AGENT_MODULE_REGISTRY.keys())}"
#             )

#         cls = _AGENT_MODULE_REGISTRY[module_type]
#         propagate = getattr(cls, "PROPAGATE_MODULES", tuple())

#         # # 1) 先继承父 env
#         # env = dict(parent_env)

#         # # 2) 再用本节点自己的 propagate 字段覆盖 env（允许子模块覆写）
#         # for key in propagate:
#         #     if key in node_cfg and node_cfg[key] is not None:
#         #         env[key] = _resolve_value(node_cfg[key], parent_env)

#         # 3) 构造本节点用于 build 的 cfg 和 obj
#         resolved_config = {}
#         resolved_modules = {}

#         # 3.1 先放默认传播参数（如果模块 cfg 没写，也能拿到）
#         #for key in propagate:
#         #    if key in parent_env:
#         #        resolved_modules[key] = parent_env[key]
            
#         # 3.2 再递归解析节点自身字段
#         for k, v in module_config.items():
#             if k in _RESERVED:
#                 continue
#             # type 保留（模块 build 可能会用到）
#             if _is_top_module_ref(k, v):
#                 resolved_modules[k] = _instantiate_top_module(v, resolved_modules)
#             else:
#                 resolved_modules[k] = v

#             #print(k, v, _is_top_module_ref(k, v))
#         # 3.3 应用全局参数
#         # try:
#         #     resolved_config = OmegaConf.merge(resolved_config, global_parameters)
#         # except:
#         #     print(resolved_config)
#         #     exit()

#         print(f"build {name} with config {module_config}")
#         #return cls.build(resolved_config, modules = resolved_modules)
    
#     # entrypoint 一般是 ${main_agent} -> DictConfig 顶层引用
#     #entry = cfg["entrypoint"]
#     ret =  _instantiate_top_module('main_agent', {})
#     print(ret)
#     exit()
# def build_agent(cfg: Union[DictConfig, dict]):
#     _lazy_import_modules()
#     if isinstance(cfg, dict):
#         cfg = OmegaConf.create(cfg)

#     if "entrypoint" not in cfg:
#         raise KeyError(f"Top config must have field `entrypoint`.\n{cfg}")

#     # 全局参数：统一用 runtime 传给所有子模块（kwargs 可覆盖）
#     global_parameters = {} if cfg.get("global_parameters") is None else cfg.get("global_parameters")



#     # def build_any(x: Any, global_parameters: dict = {}):
#     #     # list
#     #     if isinstance(x, (list, ListConfig)):
#     #         return [build_any(i) for i in list(x)]

#     #     # dict -> DictConfig
#     #     if isinstance(x, dict):
#     #         x = OmegaConf.create(x)

#     #     # DictConfig
#     #     if isinstance(x, DictConfig):
#     #         if "type" in x:
#     #             cls_name = str(x["type"])
#     #             if cls_name not in _AGENT_MODULE_REGISTRY:
#     #                 raise KeyError(
#     #                     f"Unknown module class '{cls_name}', "
#     #                     f"registered={list(_AGENT_MODULE_REGISTRY.keys())}"
#     #                 )

#     #             #resolved = {k: build_any(v) for k, v in x.items() if k not in 

#     #             print(resolved, cls_name)
#     #             return _AGENT_MODULE_REGISTRY[cls_name].build(
#     #                 OmegaConf.create(resolved), **global_parameters
#     #             )

#     #         # 普通 dict config：递归内部
#     #         return OmegaConf.create({k: build_any(v) for k, v in x.items()})

#     #     # 标量（路径字符串等）
#     #     return x

#     # entrypoint: ${main_agent} 会是 DictConfig，直接递归 build
#     # return build_any(cfg["entrypoint"])







