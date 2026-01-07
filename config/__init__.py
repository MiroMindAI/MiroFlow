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

