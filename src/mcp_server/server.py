# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import pathlib
import os
import uuid
import traceback
from typing import Any
from concurrent.futures import ThreadPoolExecutor

import dotenv
import hydra
from hydra.core.global_hydra import GlobalHydra
from fastmcp import FastMCP
from omegaconf import DictConfig, OmegaConf

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
_config_cache: dict[str, DictConfig] = {}
_executor = ThreadPoolExecutor(max_workers=4)


def _load_config(config_name: str) -> DictConfig:
    if config_name in _config_cache:
        return _config_cache[config_name]

    GlobalHydra.instance().clear()
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=config_name)
        cfg = OmegaConf.to_container(cfg, resolve=True)
        cfg = OmegaConf.create(cfg)
        _config_cache[config_name] = cfg
    return cfg


def _get_or_create_pipeline(config_name: str) -> tuple[Any, Any, Any, DictConfig]:
    if config_name not in _pipeline_cache:
        cfg = _load_config(config_name)
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


_running_tasks: dict[str, asyncio.Task] = {}
_task_results: dict[str, dict[str, Any]] = {}


@mcp.tool()
async def run_agent(
    task: str,
    task_file: str = "",
    config_name: str = "agent_quickstart_reading",
    task_id: str = "",
    wait: bool = False,
) -> dict[str, str]:
    """
    Execute a MiroFlow research agent to perform complex multi-step tasks.

    Args:
        task: The task description or question for the agent to solve.
        task_file: Optional path to a file associated with the task.
        config_name: Agent configuration (agent_quickstart_reading, agent_quickstart_search).
        task_id: Optional unique identifier. Auto-generated if not provided.
        wait: If True, wait for completion. If False, return immediately with task_id.

    Returns:
        Dictionary with task status. Use get_task_status to check results if wait=False.
    """
    if not task_id:
        task_id = f"mcp_{uuid.uuid4().hex[:8]}"

    logger.info(f"[MCP Server] Starting task: {task_id}")

    if not wait:

        async def run_in_background():
            try:
                result = await _execute_task(task, task_file, config_name, task_id)
                _task_results[task_id] = result
            except Exception as e:
                _task_results[task_id] = {
                    "task_id": task_id,
                    "status": "failed",
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                }
            finally:
                _running_tasks.pop(task_id, None)

        task_obj = asyncio.create_task(run_in_background())
        _running_tasks[task_id] = task_obj

        return {
            "task_id": task_id,
            "status": "started",
            "message": f"Task started in background. Use get_task_status('{task_id}') to check progress.",
        }

    return await _execute_task(task, task_file, config_name, task_id)


async def _execute_task(
    task: str,
    task_file: str,
    config_name: str,
    task_id: str,
) -> dict[str, Any]:
    try:
        main_agent_tool_manager, sub_agent_tool_managers, output_formatter, cfg = (
            _get_or_create_pipeline(config_name)
        )

        logs_dir = pathlib.Path(cfg.output_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
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

        logger.info(f"[MCP Server] Task {task_id} completed")

        return {
            "summary": final_summary or "",
            "answer": final_boxed_answer or "",
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
    """List available agent configurations."""
    config_dir = pathlib.Path(config_path())
    configs = []

    for f in config_dir.glob("agent_quickstart*.yaml"):
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
    }
    return descriptions.get(name, "Custom agent configuration")


@mcp.tool()
async def get_task_status(task_id: str) -> dict[str, Any]:
    """
    Get the status and results of a task.

    Args:
        task_id: The unique identifier of the task.

    Returns:
        Dictionary with task status and results.
    """
    if task_id in _running_tasks:
        return {
            "task_id": task_id,
            "status": "running",
            "message": "Task is still running",
        }

    if task_id in _task_results:
        return _task_results[task_id]

    logs_dir = pathlib.Path("logs")
    log_file = logs_dir / f"{task_id}.log"

    if not log_file.exists():
        return {
            "task_id": task_id,
            "status": "not_found",
            "message": f"No task found with id {task_id}",
        }

    try:
        import json

        with open(log_file, "r") as f:
            log_data = json.load(f)

        return {
            "task_id": task_id,
            "status": log_data.get("status", "unknown"),
            "final_answer": log_data.get("final_boxed_answer", ""),
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "message": f"Failed to read log: {str(e)}",
        }


@mcp.tool()
async def cancel_task(task_id: str) -> dict[str, str]:
    """
    Cancel a running task.

    Args:
        task_id: The unique identifier of the task to cancel.
    """
    if task_id not in _running_tasks:
        return {"status": "not_found", "message": f"No running task with id {task_id}"}

    _running_tasks[task_id].cancel()
    _running_tasks.pop(task_id, None)
    return {"status": "cancelled", "task_id": task_id}


def run_server(
    transport: str = "streamable-http",
    host: str = "0.0.0.0",
    port: int = 8000,
    path: str = "/mcp",
):
    logger.info(f"[MiroFlow MCP Server] Starting on {host}:{port}{path}")

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
        "--transport", choices=["stdio", "streamable-http"], default="streamable-http"
    )
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", type=str, default="/mcp")

    args = parser.parse_args()
    run_server(transport=args.transport, host=args.host, port=args.port, path=args.path)
