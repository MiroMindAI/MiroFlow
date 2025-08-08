# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import logging
from functools import lru_cache
from typing import Literal

from rich.console import Console
from rich.logging import RichHandler


@lru_cache
def bootstrap_logger(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | int = "DEBUG",
    logger: logging.Logger | None = None,
) -> logging.Logger:
    """Configure only this logger, not the root logger"""
    if logger is None:
        logger = logging.getLogger("miroflow")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    # use rich for better readability of stack trace.
    handler = RichHandler(
        console=Console(stderr=True),
        rich_tracebacks=True,
    )
    formatter = logging.Formatter("%(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level)
    logger.propagate = False

    return logger
