# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# This file makes the conf directory a Python package
import logging
import pathlib

import omegaconf
import yaml


def config_path() -> str:
    return str(pathlib.Path(__file__).parent.absolute())


def config_name() -> str:
    return "config"


def debug_config(cfg: omegaconf.DictConfig, logger: logging.Logger):
    full_config = omegaconf.OmegaConf.to_container(cfg, resolve=True)
    # mask the key in .env
    masked_env = {}
    assert isinstance(full_config, dict) and "env" in full_config
    for key, val in full_config["env"].items():
        if isinstance(key, str) and key.endswith("key"):
            masked_env[key] = val[:5] + "***" + val[-5:]
        else:
            masked_env[key] = val
    full_config["env"] = masked_env
    logger.info(yaml.dump(data=full_config))
