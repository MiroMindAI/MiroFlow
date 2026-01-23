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
import aiohttp
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
    instructions="""MiroFlow - AI orchestration framework with Vibe-Kanban integration.

MAIN ORCHESTRATION TOOL:
orchestrate_task(project_name, main_task, subtasks, parallel=True)
  - Automatically creates subtasks in Vibe-Kanban
  - Executes them via sub-agents (parallel or sequential)
  - Tracks progress and merges results
  - Updates Vibe-Kanban task statuses

Example:
  orchestrate_task(
    project_name="MyProject",
    main_task="Build login feature",
    subtasks=[
      {"title": "Design UI", "description": "...", "sub_agent": "agent-pixel-perfect"},
      {"title": "Implement API", "description": "...", "sub_agent": "agent-code-review"},
      {"title": "Write tests", "description": "...", "sub_agent": "agent-code-review"}
    ]
  )

MONITORING:
- get_orchestration_status(session_id) - poll until status="completed"
- get_task_status(task_id) - single task status

SUB-AGENTS:
- agent-code-review: Code quality, bugs, best practices
- agent-pixel-perfect: UI/Figma comparison
- agent-ios-developer: iOS/Swift development
- agent-rust-developer: Rust development
- agent-researcher: Web research, docs lookup
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
    """Cancel a running MiroFlow task."""
    if task_id not in _running_tasks:
        return {"status": "not_found", "message": f"No running task with id {task_id}"}

    _running_tasks[task_id].cancel()
    _running_tasks.pop(task_id, None)
    return {"status": "cancelled", "task_id": task_id}


VIBE_KANBAN_API = os.getenv("VIBE_KANBAN_API", "http://127.0.0.1:61265/api")


async def _vk_api_get(endpoint: str) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{VIBE_KANBAN_API}{endpoint}") as resp:
            return await resp.json()


async def _vk_api_post(endpoint: str, data: dict) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{VIBE_KANBAN_API}{endpoint}", json=data) as resp:
            return await resp.json()


async def _vk_api_patch(endpoint: str, data: dict) -> dict:
    async with aiohttp.ClientSession() as session:
        async with session.patch(f"{VIBE_KANBAN_API}{endpoint}", json=data) as resp:
            return await resp.json()


@mcp.tool()
async def vibe_kanban_list_projects() -> list[dict[str, str]]:
    """List all projects in Vibe-Kanban."""
    try:
        result = await _vk_api_get("/projects")
        if result.get("success"):
            return [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "working_dir": p.get("default_agent_working_dir", ""),
                }
                for p in result["data"]
            ]
        return [{"error": result.get("message", "API error")}]
    except Exception as e:
        return [{"error": f"Failed to connect to Vibe-Kanban: {e}"}]


@mcp.tool()
async def vibe_kanban_list_tasks(
    project_id: str = "", status: str = ""
) -> list[dict[str, Any]]:
    """List tasks in Vibe-Kanban. Requires project_id. Optional status filter (todo, inprogress, done, cancelled, inreview)."""
    if not project_id:
        return [{"error": "project_id is required"}]

    try:
        endpoint = f"/tasks?project_id={project_id}"
        result = await _vk_api_get(endpoint)
        if result.get("success"):
            tasks = result["data"]
            if status:
                tasks = [t for t in tasks if t["status"] == status]
            return tasks
        return [{"error": result.get("message", "API error")}]
    except Exception as e:
        return [{"error": f"Failed to connect to Vibe-Kanban: {e}"}]


@mcp.tool()
async def vibe_kanban_create_task(
    project_id: str, title: str, description: str = "", status: str = "todo"
) -> dict[str, str]:
    """Create a new task in Vibe-Kanban. Status: todo, inprogress, done, cancelled, inreview."""
    try:
        result = await _vk_api_post(
            "/tasks",
            {
                "project_id": project_id,
                "title": title,
                "description": description,
                "status": status,
            },
        )
        if result.get("success"):
            return {
                "status": "created",
                "task_id": result["data"]["id"],
                "title": title,
            }
        return {"error": result.get("message", "API error")}
    except Exception as e:
        return {"error": f"Failed to connect to Vibe-Kanban: {e}"}


@mcp.tool()
async def vibe_kanban_update_task(
    task_id: str, title: str = "", description: str = "", status: str = ""
) -> dict[str, str]:
    """Update a task in Vibe-Kanban. Provide task_id and fields to update."""
    try:
        data = {}
        if title:
            data["title"] = title
        if description:
            data["description"] = description
        if status:
            data["status"] = status

        if not data:
            return {"error": "No fields to update"}

        result = await _vk_api_patch(f"/tasks/{task_id}", data)
        if result.get("success"):
            return {"status": "updated", "task_id": task_id}
        return {"error": result.get("message", "API error")}
    except Exception as e:
        return {"error": f"Failed to connect to Vibe-Kanban: {e}"}


_orchestration_sessions: dict[str, dict[str, Any]] = {}


@mcp.tool()
async def orchestrate_task(
    project_name: str,
    main_task: str,
    subtasks: list[dict[str, str]],
    parallel: bool = True,
) -> dict[str, Any]:
    """
    Orchestrate a complex task by creating subtasks in Vibe-Kanban and executing them.

    Args:
        project_name: Vibe-Kanban project to create subtasks in
        main_task: Description of the main task being orchestrated
        subtasks: List of subtasks, each with 'title', 'description', and optional 'sub_agent'
                  Example: [{"title": "Review code", "description": "...", "sub_agent": "agent-code-review"}]
        parallel: If True, run subtasks in parallel. If False, run sequentially.

    Returns:
        Orchestration session with session_id to track progress via get_orchestration_status()
    """
    session_id = f"orch_{uuid.uuid4().hex[:8]}"

    session = {
        "session_id": session_id,
        "project_name": project_name,
        "main_task": main_task,
        "status": "initializing",
        "started_at": datetime.now().isoformat(),
        "subtasks": [],
        "results": [],
        "parallel": parallel,
    }
    _orchestration_sessions[session_id] = session

    async def run_orchestration():
        try:
            session["status"] = "creating_subtasks"

            for i, subtask in enumerate(subtasks):
                vk_result = await _create_vk_task(
                    project_name,
                    subtask.get("title", f"Subtask {i + 1}"),
                    subtask.get("description", ""),
                )

                session["subtasks"].append(
                    {
                        "index": i,
                        "title": subtask.get("title"),
                        "description": subtask.get("description", ""),
                        "sub_agent": subtask.get("sub_agent", ""),
                        "vk_task_id": vk_result.get("task_id", ""),
                        "miroflow_task_id": "",
                        "status": "created",
                        "result": None,
                    }
                )

            session["status"] = "executing"

            if parallel:
                tasks = []
                for i, subtask_info in enumerate(session["subtasks"]):
                    task_coro = _execute_subtask(session_id, i, subtask_info)
                    tasks.append(asyncio.create_task(task_coro))

                await asyncio.gather(*tasks, return_exceptions=True)
            else:
                for i, subtask_info in enumerate(session["subtasks"]):
                    await _execute_subtask(session_id, i, subtask_info)

            session["status"] = "merging"

            all_results = []
            for subtask_info in session["subtasks"]:
                if subtask_info.get("result"):
                    all_results.append(
                        {
                            "title": subtask_info["title"],
                            "answer": subtask_info["result"].get("answer", ""),
                            "summary": subtask_info["result"].get("summary", ""),
                        }
                    )

            session["merged_result"] = {
                "main_task": main_task,
                "subtask_count": len(subtasks),
                "completed_count": len(
                    [s for s in session["subtasks"] if s["status"] == "completed"]
                ),
                "results": all_results,
            }

            session["status"] = "completed"
            session["completed_at"] = datetime.now().isoformat()

            for subtask_info in session["subtasks"]:
                if subtask_info.get("vk_task_id"):
                    await _update_vk_task(subtask_info["vk_task_id"], status="done")

        except Exception as e:
            session["status"] = "failed"
            session["error"] = str(e)
            logger.error(f"Orchestration {session_id} failed: {e}")

    asyncio.create_task(run_orchestration())

    return {
        "session_id": session_id,
        "status": "started",
        "subtask_count": len(subtasks),
        "message": f"Orchestration started. Poll get_orchestration_status('{session_id}') for progress.",
    }


async def _get_project_id_by_name(project_name: str) -> str | None:
    try:
        result = await _vk_api_get("/projects")
        if result.get("success"):
            for p in result["data"]:
                if project_name.lower() in p["name"].lower():
                    return p["id"]
    except:
        pass
    return None


async def _create_vk_task(project_name: str, title: str, description: str) -> dict:
    project_id = await _get_project_id_by_name(project_name)
    if not project_id:
        return {"error": f"Project '{project_name}' not found"}

    try:
        result = await _vk_api_post(
            "/tasks",
            {
                "project_id": project_id,
                "title": title,
                "description": description,
                "status": "inprogress",
            },
        )
        if result.get("success"):
            return {"task_id": result["data"]["id"]}
        return {"error": result.get("message", "API error")}
    except Exception as e:
        return {"error": str(e)}


async def _update_vk_task(task_id: str, status: str) -> dict:
    try:
        result = await _vk_api_patch(f"/tasks/{task_id}", {"status": status})
        if result.get("success"):
            return {"status": "updated"}
        return {"error": result.get("message", "API error")}
    except Exception as e:
        return {"error": str(e)}


async def _execute_subtask(session_id: str, index: int, subtask_info: dict):
    session = _orchestration_sessions.get(session_id)
    if not session:
        return

    subtask_info["status"] = "running"

    task_description = f"{subtask_info['title']}\n\n{subtask_info['description']}"
    sub_agent = subtask_info.get("sub_agent", "")

    task_id = f"orch_{session_id}_{index}"
    subtask_info["miroflow_task_id"] = task_id

    if subtask_info.get("vk_task_id"):
        await _update_vk_task(subtask_info["vk_task_id"], status="inprogress")

    try:
        result = await _execute_task(
            task=task_description,
            task_file="",
            config_name="agent_llm_opencode_opus45",
            task_id=task_id,
            sub_agent=sub_agent,
        )

        subtask_info["status"] = (
            "completed" if result.get("status") == "completed" else "failed"
        )
        subtask_info["result"] = result

        if subtask_info.get("vk_task_id"):
            vk_status = "done" if subtask_info["status"] == "completed" else "cancelled"
            await _update_vk_task(subtask_info["vk_task_id"], status=vk_status)

    except Exception as e:
        subtask_info["status"] = "failed"
        subtask_info["error"] = str(e)
        if subtask_info.get("vk_task_id"):
            await _update_vk_task(subtask_info["vk_task_id"], status="cancelled")


@mcp.tool()
async def get_orchestration_status(session_id: str) -> dict[str, Any]:
    """Get status of an orchestration session. Poll until status='completed'."""
    session = _orchestration_sessions.get(session_id)
    if not session:
        return {"error": f"Orchestration session '{session_id}' not found"}

    subtask_summary = []
    for s in session.get("subtasks", []):
        subtask_summary.append(
            {
                "title": s.get("title"),
                "status": s.get("status"),
                "sub_agent": s.get("sub_agent", "main"),
            }
        )

    result = {
        "session_id": session_id,
        "status": session.get("status"),
        "main_task": session.get("main_task"),
        "started_at": session.get("started_at"),
        "subtasks": subtask_summary,
    }

    if session.get("completed_at"):
        result["completed_at"] = session["completed_at"]

    if session.get("merged_result"):
        result["merged_result"] = session["merged_result"]

    if session.get("error"):
        result["error"] = session["error"]

    return result


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
