# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Optional

from omegaconf import DictConfig, OmegaConf
import importlib

from src.logging.task_tracer import TaskTracer


def LLMClient(
    task_id: str,
    cfg: DictConfig = None,
    llm_config: DictConfig = None,
    task_log: Optional[TaskTracer] = None,
    **kwargs,
):
    """
    create LLMClientProvider from hydra configuration.
    Can accept either:
    - cfg: Traditional config with cfg.llm structure
    - llm_config: Direct LLM configuration
    """
    if llm_config is not None:
        # Direct LLM config provided
        provider_class = llm_config.provider_class
        # Create compatible config structure
        config = OmegaConf.create({"llm": llm_config})
        config = OmegaConf.merge(config, kwargs)
    elif cfg is not None:
        # Traditional cfg.llm structure
        provider_class = cfg.llm.provider_class
        config = OmegaConf.merge(cfg, kwargs)
    else:
        raise ValueError("Either cfg or llm_config must be provided")

    assert isinstance(config, DictConfig), "expect a dict config"

    # Dynamically import the provider class from the .providers module

    # Validate provider_class is a string and a valid identifier
    if not isinstance(provider_class, str) or not provider_class.isidentifier():
        raise ValueError(f"Invalid provider_class: {provider_class}")

    try:
        # Import the module dynamically
        providers_module = importlib.import_module("src.llm.providers")
        # Get the class from the module
        ProviderClass = getattr(providers_module, provider_class)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(
            f"Could not import class '{provider_class}' from 'src.llm.providers': {e}"
        )

    # Instantiate the client using the imported class
    try:
        client_instance = ProviderClass(task_id=task_id, task_log=task_log, cfg=config)
    except Exception as e:
        raise RuntimeError(f"Failed to instantiate {provider_class}: {e}")

    return client_instance
