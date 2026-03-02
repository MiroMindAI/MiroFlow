# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
LLM client factory module - builds LLM client instances from configuration
"""

import importlib
from typing import Optional

from omegaconf import DictConfig, OmegaConf

from miroflow.llm.base import LLMClientBase


def build_llm_client(
    cfg: Optional[DictConfig | dict | str],
    **kwargs,
) -> LLMClientBase:
    """
    Create LLMClientProvider from hydra configuration.
    Can accept either:
    - cfg: Traditional config with cfg.llm structure
    - llm_config: Direct LLM configuration
    """
    # assert cfg is not None, "cfg is required"

    if cfg is None:
        return None

    # Direct LLM config provided
    if isinstance(cfg, dict):
        cfg = OmegaConf.create(cfg)

    if "_base_" in cfg:
        base_config = OmegaConf.load(cfg["_base_"])
        cfg = OmegaConf.merge(base_config, cfg)

    provider_class = cfg.provider_class
    # Create compatible config structure
    config = OmegaConf.create(cfg)
    config = OmegaConf.merge(config, kwargs)

    assert isinstance(config, DictConfig), "expect a dict config"

    # Dynamically import the provider class from the .providers module

    # Validate provider_class is a string and a valid identifier
    if not isinstance(provider_class, str) or not provider_class.isidentifier():
        raise ValueError(f"Invalid provider_class: {provider_class}")

    try:
        # Import the module dynamically from miroflow.llm
        llm_module = importlib.import_module("miroflow.llm")
        # Get the class from the module
        ProviderClass = getattr(llm_module, provider_class)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(
            f"Could not import class '{provider_class}' from 'miroflow.llm': {e}"
        )

    # Instantiate the client using the imported class
    try:
        client_instance = ProviderClass(cfg=config)
    except Exception as e:
        raise RuntimeError(
            f"Failed to instantiate {provider_class}: {e}, llm config: {config} \n"
        )

    return client_instance
