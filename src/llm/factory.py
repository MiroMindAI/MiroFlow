# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
LLM 客户端工厂模块 - 负责从配置构建 LLM 客户端实例
"""

import importlib
from typing import Optional

from omegaconf import DictConfig, OmegaConf

from src.llm.base import LLMClientBase


def build_llm_client(
    llm_config: Optional[DictConfig | dict | str],
    **kwargs,
) -> LLMClientBase:
    """
    Create LLMClientProvider from hydra configuration.
    Can accept either:
    - cfg: Traditional config with cfg.llm structure
    - llm_config: Direct LLM configuration
    """
    assert llm_config is not None, "llm_config is required"
    
    # Direct LLM config provided
    if isinstance(llm_config, dict):
        llm_config = OmegaConf.create(llm_config)

    if "_base_" in llm_config:
        base_config = OmegaConf.load(llm_config["_base_"])
        llm_config = OmegaConf.merge(base_config, llm_config)
    
    provider_class = llm_config.provider_class
    # Create compatible config structure
    config = OmegaConf.create(llm_config)
    config = OmegaConf.merge(config, kwargs)

    assert isinstance(config, DictConfig), "expect a dict config"

    # Dynamically import the provider class from the .providers module

    # Validate provider_class is a string and a valid identifier
    if not isinstance(provider_class, str) or not provider_class.isidentifier():
        raise ValueError(f"Invalid provider_class: {provider_class}")

    try:
        # Import the module dynamically from src.llm
        llm_module = importlib.import_module("src.llm")
        # Get the class from the module
        ProviderClass = getattr(llm_module, provider_class)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(
            f"Could not import class '{provider_class}' from 'src.llm': {e}"
        )

    # Instantiate the client using the imported class
    try:
        client_instance = ProviderClass(cfg=config)
    except Exception as e:
        raise RuntimeError(f"Failed to instantiate {provider_class}: {e}, llm config: {config} \n")

    return client_instance
