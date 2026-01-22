# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import pathlib
import os
import uuid
import traceback
import json
from datetime import datetime
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
    instructions="""MiroFlow is an AI orchestration framework that manages complex multi-step tasks.

IMPORTANT FOR VIBE-KANBAN INTEGRATION:
- Use run_agent() to delegate complex research/analysis tasks
- Use get_task_status() to monitor progress and get results
- Use list_sub_agents() to see available specialized agents
- Tasks run asynchronously - check status periodically until completed

WORKFLOW:
1. Call run_agent(task="...", wait=False) to start a task
2. Poll get_task_status(task_id) every few seconds
3. When status="completed", read the answer from the result

AVAILABLE SUB-AGENTS:
- agent-code-review: Code quality analysis, best practices
- agent-pixel-perfect: UI/Figma design comparison
- agent-ios-developer: iOS/Swift development expertise
- agent-rust-developer: Rust development expertise  
- agent-researcher: Web research, documentation lookup
""",
)

_pipeline_cache: dict[str, Any] = {}
_config_cache: dict[str, Any] = {}
_executor = ThreadPoolExecutor(max_workers=4)

_task_progress: dict[str, dict[str, Any]] = {}


def _load_config(config_name: str):
    if config_name in _config_cache:
        return _config_cache[config_name]

    GlobalHydra.instance().clear()
    with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
        cfg = hydra.compose(config_name=config_name)
        resolved = OmegaConf.to_container(cfg, resolve=True)
        result = DictConfig(resolved)
        _config_cache[config_name] = result
    return result


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
    config_name: str = "agent_llm_opencode_opus45",
    task_id: str = "",
    wait: bool = False,
    sub_agent: str = "",
) -> dict[str, str]:
    """
    Execute a MiroFlow research agent to perform complex multi-step tasks.

    IMPORTANT: For Vibe-Kanban orchestration, use wait=False and poll get_task_status().

    Args:
        task: The task description or question for the agent to solve.
        task_file: Optional path to a file associated with the task.
        config_name: Agent configuration (default: agent_llm_opencode_opus45).
        task_id: Optional unique identifier. Auto-generated if not provided.
        wait: If True, wait for completion. If False, return immediately with task_id for polling.
        sub_agent: Optional sub-agent to use (agent-code-review, agent-pixel-perfect, agent-ios-developer, agent-rust-developer, agent-researcher).

    Returns:
        Dictionary with task_id and status. Poll get_task_status(task_id) until status="completed".

    Example workflow:
        1. result = run_agent(task="Review this code for bugs", wait=False)
        2. task_id = result["task_id"]
        3. Loop: status = get_task_status(task_id) until status["status"] == "completed"
        4. Read status["answer"] for the final result
    """
    if not task_id:
        task_id = f"mcp_{uuid.uuid4().hex[:8]}"

    logger.info(f"[MCP Server] Starting task: {task_id}")

    _task_progress[task_id] = {
        "task_id": task_id,
        "status": "initializing",
        "started_at": datetime.now().isoformat(),
        "task": task[:200] + "..." if len(task) > 200 else task,
        "sub_agent": sub_agent or "main",
        "steps_completed": 0,
        "current_step": "Initializing pipeline...",
    }

    if not wait:

        async def run_in_background():
            try:
                _task_progress[task_id]["status"] = "running"
                _task_progress[task_id]["current_step"] = "Executing agent..."

                result = await _execute_task(
                    task, task_file, config_name, task_id, sub_agent
                )

                _task_progress[task_id]["status"] = "completed"
                _task_progress[task_id]["completed_at"] = datetime.now().isoformat()
                _task_results[task_id] = result
            except Exception as e:
                _task_progress[task_id]["status"] = "failed"
                _task_progress[task_id]["error"] = str(e)
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
            "message": f"Task started. Poll get_task_status('{task_id}') until status='completed'.",
            "sub_agent": sub_agent or "main",
        }

    return await _execute_task(task, task_file, config_name, task_id, sub_agent)


async def _execute_task(
    task: str,
    task_file: str,
    config_name: str,
    task_id: str,
    sub_agent: str = "",
) -> dict[str, Any]:
    try:
        main_agent_tool_manager, sub_agent_tool_managers, output_formatter, cfg = (
            _get_or_create_pipeline(config_name)
        )

        logs_dir = pathlib.Path(cfg.output_dir)
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_path = logs_dir / f"{task_id}.log"

        if sub_agent and sub_agent in (sub_agent_tool_managers or {}):
            _task_progress[task_id]["current_step"] = f"Running sub-agent: {sub_agent}"

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
            "sub_agent": sub_agent or "main",
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

    priority_configs = [
        "agent_llm_opencode_opus45",
        "agent_quickstart_reading",
        "agent_quickstart_search",
    ]
    for name in priority_configs:
        if (config_dir / f"{name}.yaml").exists():
            configs.append(
                {
                    "name": name,
                    "description": _get_config_description(name),
                }
            )

    return configs


def _get_config_description(name: str) -> str:
    descriptions = {
        "agent_llm_opencode_opus45": "Claude Opus 4.5 via OpenCode OAuth (default, recommended)",
        "agent_quickstart_reading": "Document analysis with file reading (OpenRouter)",
        "agent_quickstart_search": "Web search and research tasks (OpenRouter)",
        "agent_quickstart_single_agent": "Simple single-agent mode (OpenRouter)",
    }
    return descriptions.get(name, "Custom agent configuration")


@mcp.tool()
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Get the status and results of a running or completed task. Poll this until status='completed'."""
    if task_id in _task_progress:
        progress = _task_progress[task_id].copy()

        if task_id in _task_results:
            progress.update(_task_results[task_id])

        return progress

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
        with open(log_file, "r") as f:
            log_data = json.load(f)

        return {
            "task_id": task_id,
            "status": log_data.get("status", "unknown"),
            "answer": log_data.get("final_boxed_answer", ""),
        }
    except Exception as e:
        return {
            "task_id": task_id,
            "status": "error",
            "message": f"Failed to read log: {str(e)}",
        }


@mcp.tool()
async def list_sub_agents() -> list[dict[str, str]]:
    """List available sub-agents for specialized tasks."""
    return [
        {
            "name": "agent-code-review",
            "description": "Code review, quality analysis, best practices, bug detection",
            "tools": "reading, searching, context7, code execution",
        },
        {
            "name": "agent-pixel-perfect",
            "description": "UI/UX comparison with Figma designs, visual QA",
            "tools": "reading, image-video, talk-to-figma",
        },
        {
            "name": "agent-ios-developer",
            "description": "iOS/Swift/SwiftUI development, Apple frameworks",
            "tools": "reading, searching, context7, code execution",
        },
        {
            "name": "agent-rust-developer",
            "description": "Rust development, systems programming, cargo ecosystem",
            "tools": "reading, searching, context7, code execution",
        },
        {
            "name": "agent-researcher",
            "description": "Web research, documentation lookup, information gathering",
            "tools": "searching, reading, context7, playwright browser",
        },
    ]


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
