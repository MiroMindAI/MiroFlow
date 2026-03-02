# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Agent factory module - builds Agent instances from configuration
"""

from typing import Union
from omegaconf import DictConfig, OmegaConf

from miroflow.registry import (
    get_registered_modules,
    safe_get_module_class,
    ComponentType,
    _lazy_import_modules,
)
from miroflow.agents.base import BaseAgent
from miroflow.logging.task_tracer import get_tracer

logger = get_tracer()

_RESERVED = {"entrypoint", "global_parameters"}


def build_agent_from_config(cfg: Union[DictConfig, dict]) -> BaseAgent:
    """Build Agent from complete configuration file (including entrypoint)"""
    entrypoint = cfg.get("entrypoint", None)
    # global_parameters is reserved but not currently used
    _ = cfg.get("global_parameters", None)

    return build_agent(cfg[entrypoint])


def build_agent(cfg: Union[DictConfig, dict], sequential: bool = False) -> BaseAgent:
    """
    Build an Agent instance from configuration.

    Args:
        cfg: Agent configuration, must contain a 'type' field
        sequential: Whether to execute sequentially (reserved parameter, unused)

    Returns:
        BaseAgent: The constructed Agent instance
    """
    # Ensure module is imported
    _lazy_import_modules(ComponentType.AGENT)
    _lazy_import_modules(ComponentType.IO_PROCESSOR)

    if isinstance(cfg, dict) or isinstance(cfg, list):
        cfg = OmegaConf.create(cfg)

    assert "type" in cfg, "Agent module config must have field `type`. \n" + str(cfg)

    module_class = str(cfg["type"])

    try:
        cls = safe_get_module_class(module_class)
    except KeyError:
        registered = get_registered_modules()
        raise KeyError(
            f"Unknown module class '{module_class}', "
            f"registered={list(registered.keys())}"
        )

    try:
        ret = cls(cfg=cfg)
    except Exception as e:
        print("------------------")
        print(cfg)
        error_msg = f"Error initializing module {module_class}: {e}, cfg: {cfg}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

    return ret
