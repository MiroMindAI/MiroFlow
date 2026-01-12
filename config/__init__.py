# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# This file makes the conf directory a Python package
import logging
import os
import pathlib
from typing import Tuple

import hydra
import omegaconf
import yaml


def config_path() -> str:
    return str(pathlib.Path(__file__).parent.absolute())


def config_name() -> str:
    return "config"

def load_config(config_file_name: str, *overrides) -> omegaconf.DictConfig:
    """
    Initialize Hydra and load configuration.
    
    Args:
        config_file_name: Name of the config file to load
        *overrides: Additional Hydra overrides
        
    Returns:
        DictConfig: Loaded and resolved configuration
    """
    hydra.initialize_config_dir(
        config_dir=os.path.abspath(config_path()), 
        version_base=None
    )
    cfg = hydra.compose(config_name=config_file_name, overrides=list(overrides))
    cfg = omegaconf.OmegaConf.create(omegaconf.OmegaConf.to_container(cfg, resolve=True))
    return cfg