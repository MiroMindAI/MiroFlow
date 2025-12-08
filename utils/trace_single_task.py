# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import logging
import pathlib
from pathlib import Path
import dotenv
import hydra

from src.logging.logger import bootstrap_logger
from config import config_name, config_path, debug_config
from src.agents.orchestrator import Orchestrator
from omegaconf import DictConfig


async def single_task(
    cfg: DictConfig,
    logger: logging.Logger,
    task_id: str = "task_1",
    task_description: str = "Write a python code to say 'Hello, World!', use python to execute the code.",
    task_file_name: str = "",
) -> None:
    """Asynchronous main function."""
    debug_config(cfg, logger)

    task_name = task_id
    log_path = pathlib.Path(".") / pathlib.Path(cfg.output_dir) / f"{task_name}.log"
    logger.info(f"logger_path is {log_path.absolute()}")

    # 创建 Orchestrator（可复用）
    orchestrator = Orchestrator(cfg=cfg)
    
    # 执行任务
    result, task_log = await orchestrator.run_task(
        task_name=task_name,
        task_id=task_id,
        task_description=task_description,
        task_file_name=task_file_name,
        log_path=log_path.absolute(),
    )
    
    logger.info(f"Task {task_id} completed with status: {task_log.status}")


def main(
    *args,
    task_id: str = "task_1",
    task: str = "Write a python code to say 'Hello, World!', use python to execute the code.",
    task_file_name: str = "",
    config_file_name: str = "",
):
    if config_file_name:
        chosen_config_name = config_file_name
    else:
        chosen_config_name = config_name()

    dotenv.load_dotenv()
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=chosen_config_name, overrides=list(args))
        logger = bootstrap_logger(level="DEBUG", to_console=True)

        # Test if logger is working
        logger.info("Logger initialized successfully")

        # Tracing functionality removed - miroflow-contrib deleted
        asyncio.run(single_task(cfg, logger, str(task_id), task, task_file_name))
