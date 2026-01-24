# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import pathlib
from datetime import datetime

import hydra
import omegaconf


def load_config(config_path: str, *overrides) -> omegaconf.DictConfig:
    """Initialize Hydra and load configuration with timestamped output directory."""
    # Extract config name (remove "config/" prefix and file extension)
    config_name = config_path
    if config_name.startswith("config/"):
        config_name = config_name[7:]
    if config_name.endswith((".yaml", ".yml")):
        config_name = os.path.splitext(config_name)[0]

    # Check if output_dir is explicitly specified in overrides
    output_dir_override = None
    for override in overrides:
        if override.startswith("output_dir="):
            output_dir_override = override.split("=", 1)[1]
            break

    # Load and resolve configuration
    hydra.initialize_config_dir(
        config_dir=str(pathlib.Path(__file__).parent.absolute()), version_base=None
    )
    cfg = hydra.compose(config_name=config_name, overrides=list(overrides))
    cfg = omegaconf.OmegaConf.create(
        omegaconf.OmegaConf.to_container(cfg, resolve=True)
    )

    # Create timestamped output directory only if output_dir was not explicitly specified
    if output_dir_override is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = pathlib.Path(cfg.output_dir) / f"{config_name}_{timestamp}"
        output_dir.mkdir(parents=True, exist_ok=True)
        cfg.output_dir = str(output_dir)
    else:
        # Use the explicitly specified output_dir directly
        output_dir = pathlib.Path(cfg.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        cfg.output_dir = str(output_dir)

    return cfg
