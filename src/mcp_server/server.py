# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import pathlib
import os
import uuid
from typing import Any

import dotenv
import hydra
from fastmcp import FastMCP
from omegaconf import DictConfig

from src.logging.logger import bootstrap_logger
from src.core.pipeline import create_pipeline_components, execute_task_pipeline
from config import config_path

dotenv.load_dotenv()

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)

mcp = FastMCP(
    "MiroFlow",
    instructions="MiroFlow is a high-performance research agent framework for complex reasoning tasks. Use run_agent to execute research tasks with web search, file reading, and multi-step reasoning capabilities.",
)

_pipeline_cache: dict[str, Any] = {}


def _get_or_create_pipeline(config_name: str) -> tuple[Any, Any, Any, DictConfig]:
    if config_name not in _pipeline_cache:
        with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
            cfg = hydra.compose(config_name=config_name)
            logs_dir = str(pathlib.Path(cfg.output_dir))
            main_agent_tool_manager, sub_agent_tool_managers, output_formatter = (
                create_pipeline_components(cfg, logs_dir=logs_dir)
            )
            _pipeline_cache[config_name] = (
                main_agent_tool_manager,
                sub_agent_tool_managers,
                output_formatter,
                cfg,
            )
    return _pipeline_cache[config_name]


@mcp.tool()
async def run_agent(
    task: str,
    task_file: str = "",
    config_name: str = "agent_quickstart_reading",
    task_id: str = "",
) -> dict[str, str]:
    """
    Execute a MiroFlow research agent to perform complex multi-step tasks.

    The agent can search the web, read files, execute code, and perform
    multi-step reasoning to answer complex questions.

    Args:
        task: The task description or question for the agent to solve.
              Be specific and detailed for best results.
        task_file: Optional path to a file associated with the task
                   (e.g., PDF, Excel, CSV for analysis).
        config_name: Agent configuration to use. Available configs:
                     - agent_quickstart_reading: For document analysis tasks
                     - agent_quickstart_search: For web search tasks
                     - agent_quickstart_single_agent: Simple single-agent mode
        task_id: Optional unique identifier for this task run.
                 Auto-generated if not provided.

    Returns:
        Dictionary with 'summary' (detailed analysis) and 'answer' (final answer).
    """
    if not task_id:
        task_id = f"mcp_task_{uuid.uuid4().hex[:8]}"

    logger.info(f"[MCP Server] Starting task: {task_id}")
    logger.info(f"[MCP Server] Task description: {task[:200]}...")

    try:
        main_agent_tool_manager, sub_agent_tool_managers, output_formatter, cfg = (
            _get_or_create_pipeline(config_name)
        )

        logs_dir = pathlib.Path(cfg.output_dir)
        log_path = logs_dir / f"{task_id}.log"

        final_summary, final_boxed_answer, log_file_path = await execute_task_pipeline(
            cfg=cfg,
            task_name=task_id,
            task_id=task_id,
            task_description=task,
            task_file_name=task_file if task_file else None,
            main_agent_tool_manager=main_agent_tool_manager,
            sub_agent_tool_managers=sub_agent_tool_managers,
            output_formatter=output_formatter,
            log_path=log_path.absolute(),
        )

        logger.info(f"[MCP Server] Task {task_id} completed successfully")

        return {
            "summary": final_summary,
            "answer": final_boxed_answer,
            "task_id": task_id,
            "log_path": str(log_file_path),
            "status": "completed",
        }

    except Exception as e:
        logger.error(f"[MCP Server] Task {task_id} failed: {e}")
        return {
            "summary": f"Task execution failed: {str(e)}",
            "answer": "",
            "task_id": task_id,
            "log_path": "",
            "status": "failed",
            "error": str(e),
        }


@mcp.tool()
async def list_configs() -> list[dict[str, str]]:
    """
    List available agent configurations.

    Returns a list of available configuration files that can be used
    with the run_agent tool's config_name parameter.
    """
    config_dir = pathlib.Path(config_path())
    configs = []

    for f in config_dir.glob("agent_*.yaml"):
        name = f.stem
        configs.append(
            {
                "name": name,
                "description": _get_config_description(name),
            }
        )

    return configs


def _get_config_description(name: str) -> str:
    descriptions = {
        "agent_quickstart_reading": "Document analysis with file reading capabilities",
        "agent_quickstart_search": "Web search and research tasks",
        "agent_quickstart_single_agent": "Simple single-agent mode for basic tasks",
        "agent_gaia-validation_claude37sonnet": "GAIA benchmark with Claude 3.7 Sonnet",
        "agent_hle_claude37sonnet": "HLE benchmark configuration",
        "agent_browsecomp-en_claude37sonnet": "BrowseComp English benchmark",
        "agent_browsecomp-zh_claude37sonnet": "BrowseComp Chinese benchmark",
    }
    return descriptions.get(name, "Custom agent configuration")


@mcp.tool()
async def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Get the status and results of a previously executed task.

    Args:
        task_id: The unique identifier of the task to check.

    Returns:
        Dictionary with task status, results, and log information.
    """
    logs_dir = pathlib.Path("logs")
    log_file = logs_dir / f"{task_id}.log"

    if not log_file.exists():
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": f"No log file found for task {task_id}",
        }

    try:
        import json

        with open(log_file, "r") as f:
            log_data = json.load(f)

        return {
            "task_id": task_id,
            "status": log_data.get("status", "unknown"),
            "final_answer": log_data.get("final_boxed_answer", ""),
            "start_time": log_data.get("start_time", ""),
            "end_time": log_data.get("end_time", ""),
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "message": f"Failed to read log file: {str(e)}",
        }


def run_server(
    transport: str = "streamable-http",
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/mcp",
):
    logger.info(f"[MiroFlow MCP Server] Starting on {host}:{port}{path}")
    logger.info(f"[MiroFlow MCP Server] Transport: {transport}")

    if transport == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(
            transport="streamable-http",
            host=host,
            port=port,
            path=path,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MiroFlow MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http", "streamable-http"],
        default="streamable-http",
        help="Transport method (default: streamable-http)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to use (default: 8000)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="/mcp",
        help="URL path for MCP endpoint (default: /mcp)",
    )

    args = parser.parse_args()

    run_server(
        transport=args.transport,
        host=args.host,
        port=args.port,
        path=args.path,
    )
