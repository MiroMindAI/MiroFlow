# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import pathlib
import traceback
import os
from datetime import datetime
from omegaconf import DictConfig

from src.llm.client import LLMClient
from src.logging.logger import bootstrap_logger
from src.logging.task_tracer import TaskTracer
from src.core.orchestrator import Orchestrator
from src.tool.manager import ToolManager
from src.utils.io_utils import OutputFormatter
from src.utils.tool_utils import create_mcp_server_parameters

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


async def execute_task_pipeline(
    cfg: DictConfig,
    task_name: str,
    task_id: str,
    task_description: str,
    task_file_name: str | None,
    main_agent_tool_manager: ToolManager,
    sub_agent_tool_managers: dict[str, ToolManager],
    output_formatter: OutputFormatter,
    log_path: pathlib.Path,
    ground_truth: str | None = None,
    metadata: dict | None = None,
) -> tuple[str, str, pathlib.Path]:
    """
    Executes the full pipeline for a single task.

    Args:
        cfg: The Hydra configuration object.
        task_description: The description of the task for the LLM.
        task_file_name: The path to an associated file (optional).
        task_id: A unique identifier for this task run (used for logging).
        main_agent_tool_manager: An initialized main agent ToolManager instance.
        sub_agent_tool_managers: A dictionary of initialized sub-agent ToolManager instances.
        output_formatter: An initialized OutputFormatter instance.
        ground_truth: The ground truth for the task (optional).
        log_dir: The directory to save the task log (default: "logs").

    Returns:
        A tuple containing:
        - A string with the final execution log and summary, or an error message.
        - The final boxed answer.
        - The path to the log file.
    """
    logger.debug(f"Starting Task Execution: {task_id}")

    # Create task log
    task_log = TaskTracer(
        log_path=log_path,
        task_name=task_name,
        task_id=task_id,
        task_file_name=task_file_name,
        ground_truth=ground_truth,
        input={
            "task_description": task_description, 
            "task_file_name": task_file_name,
            "metadata": metadata or {}
        },
    )

    main_agent_llm_client = None
    sub_agent_llm_client = None
    final_answer, final_boxed_answer = "", ""
    try:
        # Initialize main agent LLM client
        # Require agent-specific LLM configuration
        if hasattr(cfg.main_agent, "llm") and cfg.main_agent.llm is not None:
            main_agent_llm_client = LLMClient(
                task_id=task_id, llm_config=cfg.main_agent.llm
            )
        else:
            raise ValueError(
                "No LLM configuration found in main_agent. Please ensure the agent configuration includes an LLM section."
            )

        # Initialize sub agent LLM client
        # Require agent-specific LLM configuration for sub-agents
        if cfg.sub_agents:
            first_sub_agent = next(iter(cfg.sub_agents.values()))
            if hasattr(first_sub_agent, "llm") and first_sub_agent.llm is not None:
                sub_agent_llm_client = LLMClient(
                    task_id=f"{task_id}_sub", llm_config=first_sub_agent.llm
                )
            else:
                raise ValueError(
                    "No LLM configuration found in sub-agent. Please ensure the agent configuration includes an LLM section."
                )
        else:
            raise ValueError(
                "No sub agents defined. Please ensure the agent configuration includes sub-agent sections."
            )

        # Initialize orchestrator
        orchestrator = Orchestrator(
            main_agent_tool_manager=main_agent_tool_manager,
            sub_agent_tool_managers=sub_agent_tool_managers,
            llm_client=main_agent_llm_client,
            sub_agent_llm_client=sub_agent_llm_client,
            output_formatter=output_formatter,
            task_log=task_log,
            cfg=cfg,
        )

        task_log.status = "running"
        final_answer, final_boxed_answer = await orchestrator.run_main_agent(
            task_description=task_description,
            task_file_name=task_file_name,
            task_id=task_id,
        )

        task_log.final_boxed_answer = final_boxed_answer
        task_log.status = "completed"

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"An error occurred during task {task_id}", exc_info=True)

        final_answer = (
            f"Error executing task {task_id}:\n"
            f"Description: {task_description}\n"
            f"File: {task_file_name}\n"
            f"Error Type: {type(e).__name__}\n"
            f"Error Details:\n{error_details}"
        )

        task_log.status = "interrupted"
        task_log.error = error_details

    finally:
        if main_agent_llm_client is not None:
            main_agent_llm_client.close()
        if (
            sub_agent_llm_client != main_agent_llm_client
            and sub_agent_llm_client is not None
        ):
            sub_agent_llm_client.close()
        task_log.end_time = datetime.now()

        # Record task summary to structured log
        task_log.log_step(
            "task_execution_finished",
            f"Task {task_id} execution completed with status: {task_log.status}",
        )
        task_log.log_step(
            "console_summary_display", "Displaying task summary to console"
        )
        task_log.save()
        logger.debug(f"--- Finished Task Execution: {task_id} ---")

        return final_answer, final_boxed_answer, task_log.log_path


def create_pipeline_components(cfg: DictConfig, logs_dir: str | None = None):
    """
    Creates and initializes the core components of the agent pipeline.

    Args:
        cfg: The Hydra configuration object.

    Returns:
        Tuple of (main_agent_tool_manager, sub_agent_tool_managers, output_formatter)
    """
    # Create ToolManagers for main agent and sub-agents
    main_agent_mcp_server_configs, main_agent_blacklist = create_mcp_server_parameters(
        cfg, cfg.main_agent, logs_dir
    )
    main_agent_tool_manager = ToolManager(
        main_agent_mcp_server_configs,
        tool_blacklist=main_agent_blacklist,
    )

    sub_agent_tool_managers = {}
    for sub_agent in cfg.sub_agents:
        sub_agent_mcp_server_configs, sub_agent_blacklist = (
            create_mcp_server_parameters(cfg, cfg.sub_agents[sub_agent], logs_dir)
        )
        sub_agent_tool_manager = ToolManager(
            sub_agent_mcp_server_configs,
            tool_blacklist=sub_agent_blacklist,
        )
        sub_agent_tool_managers[sub_agent] = sub_agent_tool_manager

    # Create OutputFormatter
    output_formatter = OutputFormatter()

    return main_agent_tool_manager, sub_agent_tool_managers, output_formatter
