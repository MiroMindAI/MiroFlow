# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import pathlib
import traceback
from datetime import datetime
from omegaconf import DictConfig, OmegaConf

from miroflow.contrib.tracing import trace
from miroflow.llm.client import LLMClient
from miroflow.logging.logger import bootstrap_logger
from miroflow.logging.task_tracer import TaskTracer, env_info, process_spans_for_summary
from miroflow.logging.tracing_processor import setup_file_trace_processor
from miroflow.prebuilt.orchestrator import Orchestrator
from miroflow.tool.manager import ToolManager
from miroflow.utils.io_utils import OutputFormatter
from miroflow.utils.tool_utils import create_mcp_server_parameters

logger = bootstrap_logger()


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
        input={"task_description": task_description, "task_file_name": task_file_name},
        env_info=env_info(cfg),
    )

    traces = []
    llm_client = None
    sub_agent_llm_client = None
    final_answer, final_boxed_answer = "", ""
    try:
        with trace(workflow_name="benchmark_workflow", trace_id=task_id):
            # Initialize main agent LLM client
            main_agent_llm_config = cfg.agent.get("main_agent_llm", None)
            if main_agent_llm_config:
                config_path = (
                    pathlib.Path(__file__).parent
                    / "config"
                    / "llm"
                    / f"{main_agent_llm_config}.yaml"
                )
                main_agent_cfg = OmegaConf.load(config_path)
                # Create a config that includes both the LLM config and the env section
                combined_cfg = OmegaConf.create({"llm": main_agent_cfg, "env": cfg.env})
                llm_client = LLMClient(task_id=task_id, cfg=combined_cfg)
            else:
                llm_client = LLMClient(task_id=task_id, cfg=cfg)

            # Initialize sub agent LLM client
            sub_agent_llm_config = cfg.agent.get("sub_agent_llm", None)
            if sub_agent_llm_config:
                config_path = (
                    pathlib.Path(__file__).parent
                    / "config"
                    / "llm"
                    / f"{sub_agent_llm_config}.yaml"
                )
                sub_agent_cfg = OmegaConf.load(config_path)
                # Create a config that includes both the LLM config and the env section
                combined_cfg = OmegaConf.create({"llm": sub_agent_cfg, "env": cfg.env})
                sub_agent_llm_client = LLMClient(
                    task_id=f"{task_id}_sub", cfg=combined_cfg
                )
            else:
                sub_agent_llm_client = llm_client  # Use the same client

            # Initialize orchestrator
            orchestrator = Orchestrator(
                main_agent_tool_manager=main_agent_tool_manager,
                sub_agent_tool_managers=sub_agent_tool_managers,
                llm_client=llm_client,
                sub_agent_llm_client=sub_agent_llm_client,
                output_formatter=output_formatter,
                task_log=task_log,
                cfg=cfg,
            )

            trace_processor = setup_file_trace_processor()
            task_log.status = "running"
            final_answer, final_boxed_answer = await orchestrator.run_main_agent(
                task_description=task_description,
                task_file_name=task_file_name,
                task_id=task_id,
            )

            traces = trace_processor.get_and_clear_traces(task_id=task_id)
            if traces:
                task_log.trace_data = process_spans_for_summary(traces[0], cfg)

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
        if llm_client is not None:
            llm_client.close()
        if sub_agent_llm_client != llm_client and sub_agent_llm_client is not None:
            sub_agent_llm_client.close()
        task_log.end_time = datetime.now()
        # log.update_cost_estimate()  # Update cost estimate

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
        cfg, cfg.agent.main_agent, logs_dir
    )
    main_agent_tool_manager = ToolManager(
        main_agent_mcp_server_configs,
        tool_blacklist=main_agent_blacklist,
    )

    sub_agent_tool_managers = {}
    for sub_agent in cfg.agent.sub_agents:
        sub_agent_mcp_server_configs, sub_agent_blacklist = (
            create_mcp_server_parameters(cfg, cfg.agent.sub_agents[sub_agent], logs_dir)
        )
        sub_agent_tool_manager = ToolManager(
            sub_agent_mcp_server_configs,
            tool_blacklist=sub_agent_blacklist,
        )
        sub_agent_tool_managers[sub_agent] = sub_agent_tool_manager

    # Create OutputFormatter
    output_formatter = OutputFormatter()

    return main_agent_tool_manager, sub_agent_tool_managers, output_formatter
