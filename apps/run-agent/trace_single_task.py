import asyncio
import logging
import pathlib
from pathlib import Path
import dotenv
import hydra
from miroflow.contrib.tracing import set_tracing_disabled, set_tracing_export_api_key
from miroflow.contrib.tracing.otlp_setup import bootstrap_silent_trace_provider
from miroflow.logging.logger import bootstrap_logger
from miroflow.prebuilt.config import config_name, config_path, debug_config
from miroflow.prebuilt.pipeline import (
    create_pipeline_components,
    execute_task_pipeline,
)
from omegaconf import DictConfig


async def single_task(
    cfg: DictConfig,
    logger: logging.Logger,
    task_id: str = "task_1",
    task_description: str = "Write a python code to say 'Hello, World!', use python to execute the code.",
    task_file_name: str = "",
) -> None:
    """Asynchrono us main function."""
    debug_config(cfg, logger)
    logs_dir = Path(cfg.output_dir)
    main_agent_tool_manager, sub_agent_tool_managers, output_formatter = (
        create_pipeline_components(cfg, logs_dir=str(logs_dir))
    )

    task_name = task_id
    log_path = pathlib.Path(".") / pathlib.Path(cfg.output_dir) / f"{task_name}.log"
    logger.info(f"logger_path is {log_path.absolute()}")

    # Execute task using the pipeline
    final_summary, final_boxed_answer, _ = await execute_task_pipeline(
        cfg=cfg,
        task_name=task_name,
        task_id=task_id,
        task_file_name=task_file_name,
        task_description=task_description,
        main_agent_tool_manager=main_agent_tool_manager,
        sub_agent_tool_managers=sub_agent_tool_managers,
        output_formatter=output_formatter,
        # relative to the folder where shell command is launched.
        log_path=log_path.absolute(),
    )

    # Print task result
    logger.info(
        f"Final Output for Task: {task_id}, summary = {final_summary}, boxed_answer = {final_boxed_answer}"
    )


def main(
    *args,
    task_id: str = "task_1",
    task: str = "Write a python code to say 'Hello, World!', use python to execute the code.",
    task_file_name: str = "",
):
    print("inside trace")
    dotenv.load_dotenv()
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=config_name(), overrides=list(args))
        logger = bootstrap_logger()
        # disable tracing and give a fake key
        set_tracing_disabled(True)
        set_tracing_export_api_key("fake-key")
        # suppress warning from trace_provider
        bootstrap_silent_trace_provider()
        asyncio.run(single_task(cfg, logger, task_id, task, task_file_name))
