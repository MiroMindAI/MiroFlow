# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Background task execution for agent runs."""

import asyncio
import os
import sys
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any

# Add parent directory for MiroFlow imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from ..core.config import AppConfig
from ..core.session_manager import SessionManager
from ..models.task import FileInfo


class TaskExecutor:
    """Executes agent tasks in background threads."""

    def __init__(self, config: AppConfig, session_manager: SessionManager):
        self.config = config
        self.session_manager = session_manager
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent_tasks)
        self._running_tasks: dict[str, threading.Thread] = {}
        self._task_tracers: dict[str, Any] = {}

    def submit_task(
        self,
        task_id: str,
        task_description: str,
        config_path: str,
        file_info: FileInfo | None = None,
    ) -> None:
        """Submit a task for background execution."""
        thread = threading.Thread(
            target=self._run_task_sync,
            args=(task_id, task_description, config_path, file_info),
            daemon=True,
        )
        self._running_tasks[task_id] = thread
        thread.start()

    def _run_task_sync(
        self,
        task_id: str,
        task_description: str,
        config_path: str,
        file_info: FileInfo | None,
    ) -> None:
        """Synchronous wrapper for async task execution."""
        asyncio.run(self._run_task(task_id, task_description, config_path, file_info))

    async def _run_task(
        self,
        task_id: str,
        task_description: str,
        config_path: str,
        file_info: FileInfo | None,
    ) -> None:
        """Execute agent task asynchronously."""
        # Change to project root for relative imports
        os.chdir(self.config.project_root)

        tracer = None

        try:
            # Import MiroFlow components (import here to avoid circular imports)
            from config import load_config
            from src.agents import build_agent_from_config
            from src.agents.context import AgentContext
            from src.logging.task_tracer import get_tracer, set_tracer

            # Update status to running
            self.session_manager.update_task(task_id, {"status": "running"})

            # Create unique output directory
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            run_id = str(uuid.uuid4())[:8]
            output_dir = self.config.logs_dir / f"{timestamp}_{run_id}"
            output_dir.mkdir(parents=True, exist_ok=True)

            # Load configuration
            cfg = load_config(config_path, f"output_dir={output_dir}")

            # Get max_turns from config
            max_turns = 30
            if hasattr(cfg, "main_agent") and hasattr(cfg.main_agent, "max_turns"):
                max_turns = cfg.main_agent.max_turns

            # Update session with log path and max_turns
            self.session_manager.update_task(
                task_id,
                {
                    "log_path": str(output_dir),
                    "max_turns": max_turns,
                },
            )

            # Setup tracer
            set_tracer(cfg.output_dir)
            tracer = get_tracer()
            tracer.set_log_path(cfg.output_dir)
            self._task_tracers[task_id] = tracer

            # Build agent
            agent = build_agent_from_config(cfg=cfg)

            # Build context
            ctx_kwargs: dict[str, Any] = {"task_description": task_description}

            if file_info:
                ctx_kwargs["file_input"] = {
                    "file_name": file_info.file_name,
                    "file_type": file_info.file_type,
                    "absolute_file_path": file_info.absolute_file_path,
                }

            ctx = AgentContext(**ctx_kwargs)

            # Start tracer
            tracer.start()
            tracer.update_task_meta(
                {
                    "task_id": task_id,
                    "task_description": task_description,
                }
            )

            # Run agent
            result = await agent.run(ctx)

            # Get final message history before cleanup
            final_messages = self._get_all_messages_from_tracer(tracer)

            # Update session with results and full message history
            self.session_manager.update_task(
                task_id,
                {
                    "status": "completed",
                    "final_answer": result.get("final_boxed_answer", ""),
                    "summary": result.get("summary", ""),
                    "messages": final_messages,
                },
            )

            tracer.finish(status="completed")

        except Exception as e:
            error_msg = f"{e!s}\n{traceback.format_exc()}"
            self.session_manager.update_task(
                task_id,
                {
                    "status": "failed",
                    "error_message": error_msg,
                },
            )
            if tracer:
                tracer.finish(status="failed", error=str(e))

        finally:
            # Cleanup
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]
            if task_id in self._task_tracers:
                del self._task_tracers[task_id]

    def _get_all_messages_from_tracer(self, tracer: Any) -> list[dict]:
        """Extract all messages from tracer for persistence."""
        try:
            with tracer._data_lock:
                for key, log_file in tracer._active_tasks.items():
                    agent_states = log_file.agent_states
                    for agent_name, state in agent_states.items():
                        state_data = (
                            state.state
                            if hasattr(state, "state")
                            else state.get("state", {})
                        )
                        message_history = state_data.get("message_history", [])
                        return self._format_messages(message_history)
        except Exception:
            pass
        return []

    def get_task_progress(self, task_id: str) -> dict[str, Any]:
        """Get current progress from tracer."""
        tracer = self._task_tracers.get(task_id)
        if tracer is None:
            return {
                "current_turn": 0,
                "step_count": 0,
                "recent_logs": [],
                "messages": [],
            }

        try:
            with tracer._data_lock:
                for key, log_file in tracer._active_tasks.items():
                    agent_states = log_file.agent_states
                    step_logs = log_file.step_logs

                    # Calculate turn count and get message history
                    current_turn = 0
                    messages = []
                    for agent_name, state in agent_states.items():
                        state_data = (
                            state.state
                            if hasattr(state, "state")
                            else state.get("state", {})
                        )
                        message_history = state_data.get("message_history", [])
                        current_turn = max(
                            current_turn, (len(message_history) + 1) // 2
                        )
                        # Get ALL messages for display (full history)
                        messages = self._format_messages(message_history)

                    # Filter and format logs to show tool calls
                    recent_logs = (
                        self._format_recent_logs(step_logs[-30:]) if step_logs else []
                    )

                    return {
                        "current_turn": current_turn,
                        "step_count": len(step_logs),
                        "recent_logs": recent_logs,
                        "messages": messages,
                    }
        except Exception:
            pass

        return {"current_turn": 0, "step_count": 0, "recent_logs": [], "messages": []}

    def _format_recent_logs(self, logs: list[dict]) -> list[dict]:
        """Format and filter logs to show relevant tool call and LLM information."""
        formatted = []
        for log in logs:
            log_type = log.get("type", "")

            # Include tool calls and results
            if (
                "tool" in log_type.lower()
                or log.get("tool_name")
                or log.get("server_name")
            ):
                formatted.append(
                    {
                        "type": "tool_call",
                        "tool_name": log.get("tool_name", ""),
                        "server_name": log.get("server_name", ""),
                        "input": self._truncate_output(
                            log.get("input") or log.get("arguments") or log.get("args")
                        ),
                        "output": self._truncate_output(
                            log.get("output") or log.get("result") or log.get("content")
                        ),
                    }
                )
            # Include LLM calls
            elif "llm" in log_type.lower() or log.get("model") or log.get("prompt"):
                formatted.append(
                    {
                        "type": "llm_call",
                        "model": log.get("model", ""),
                        "input": self._truncate_output(
                            log.get("prompt") or log.get("input") or log.get("messages")
                        ),
                        "output": self._truncate_output(
                            log.get("response")
                            or log.get("output")
                            or log.get("content")
                        ),
                    }
                )
            # Include span events (shows execution flow)
            elif log_type in ("span_start", "span_end"):
                path = log.get("path", "")
                # Only include interesting spans
                if any(
                    x in path.lower()
                    for x in ["tool", "search", "read", "llm", "agent", "mcp"]
                ):
                    formatted.append(
                        {
                            "type": log_type,
                            "path": path,
                            "name": path.split("/")[-1] if path else "",
                        }
                    )
            # Include any log with tool-related or LLM-related fields
            elif any(
                key in log
                for key in ["tool_name", "server_name", "tool_call", "model", "prompt"]
            ):
                formatted.append(log)

        # Return last 15 formatted logs
        return formatted[-15:]

    def _format_messages(self, messages: list[dict]) -> list[dict]:
        """Format message history for display.

        Note: We do NOT truncate message content here to preserve:
        - Full thinking/reasoning content for proper display
        - Complete tool results (e.g., search results JSON) for parsing
        """
        formatted = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            # Handle different content types
            if isinstance(content, list):
                # Tool results or multi-part content
                text_parts = []
                for item in content:
                    if isinstance(item, dict):
                        if item.get("type") == "text":
                            text_parts.append(item.get("text", ""))
                        elif item.get("type") == "tool_result":
                            # Don't truncate tool results - need full JSON for parsing
                            tool_content = item.get("content", "")
                            if isinstance(tool_content, str):
                                text_parts.append(tool_content)
                            else:
                                text_parts.append(str(tool_content))
                        elif item.get("type") == "tool_use":
                            text_parts.append(f"[Tool Call: {item.get('name', '')}]")
                    elif isinstance(item, str):
                        text_parts.append(item)
                content = "\n".join(text_parts)
            elif not isinstance(content, str):
                content = str(content)

            # Don't truncate - preserve full content for thinking and tool results
            formatted.append(
                {
                    "role": role,
                    "content": content,
                }
            )

        return formatted

    def _truncate_output(self, output: Any) -> Any:
        """Truncate long output strings."""
        if output is None:
            return None
        if isinstance(output, str) and len(output) > 1000:
            return output[:1000] + "... (truncated)"
        return output

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task (best effort - marks as cancelled)."""
        if task_id in self._running_tasks:
            self.session_manager.update_task(
                task_id,
                {
                    "status": "cancelled",
                    "error_message": "Task cancelled by user",
                },
            )
            return True
        return False

    def is_task_running(self, task_id: str) -> bool:
        """Check if a task is currently running."""
        return task_id in self._running_tasks
