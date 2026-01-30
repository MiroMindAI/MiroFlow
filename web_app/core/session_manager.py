# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""File-based session management for tasks."""

import json
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

from ..models.task import FileInfo, TaskResponse, TaskStatus


class SessionManager:
    """Manages task sessions stored as JSON files."""

    def __init__(self, sessions_dir: Path):
        self.sessions_dir = sessions_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _get_session_path(self, task_id: str) -> Path:
        """Get path to session file for a task."""
        return self.sessions_dir / f"{task_id}.json"

    def _read_session(self, task_id: str) -> dict[str, Any] | None:
        """Read session data from file."""
        path = self._get_session_path(task_id)
        if not path.exists():
            return None
        with self._lock:
            with open(path, encoding="utf-8") as f:
                return json.load(f)

    def _write_session(self, task_id: str, data: dict[str, Any]) -> None:
        """Write session data to file atomically."""
        path = self._get_session_path(task_id)
        temp_path = path.with_suffix(".tmp")
        with self._lock:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(temp_path, path)

    def create_task(
        self,
        task_id: str,
        task_description: str,
        config_path: str,
        file_info: FileInfo | None = None,
        log_path: str | None = None,
        max_turns: int = 0,
    ) -> TaskResponse:
        """Create a new task session."""
        now = datetime.utcnow()
        session = {
            "id": task_id,
            "task_description": task_description,
            "config_path": config_path,
            "status": "pending",
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "current_turn": 0,
            "max_turns": max_turns,
            "step_count": 0,
            "final_answer": None,
            "summary": None,
            "error_message": None,
            "file_info": file_info.model_dump() if file_info else None,
            "log_path": log_path,
        }
        self._write_session(task_id, session)
        return TaskResponse(**session)

    def get_task(self, task_id: str) -> TaskResponse | None:
        """Get task by ID."""
        session = self._read_session(task_id)
        if session is None:
            return None
        return TaskResponse(**session)

    def list_tasks(
        self,
        page: int = 1,
        page_size: int = 20,
        status: TaskStatus | None = None,
    ) -> tuple[list[TaskResponse], int]:
        """List all tasks with pagination."""
        tasks = []
        for path in self.sessions_dir.glob("*.json"):
            session = self._read_session(path.stem)
            if session:
                if status is None or session.get("status") == status:
                    tasks.append(TaskResponse(**session))

        # Sort by created_at descending (newest first)
        tasks.sort(key=lambda t: t.created_at, reverse=True)

        # Paginate
        total = len(tasks)
        start = (page - 1) * page_size
        end = start + page_size
        return tasks[start:end], total

    def update_task(self, task_id: str, updates: dict[str, Any]) -> TaskResponse | None:
        """Update task session with new values."""
        session = self._read_session(task_id)
        if session is None:
            return None

        session.update(updates)
        session["updated_at"] = datetime.utcnow().isoformat()
        self._write_session(task_id, session)
        return TaskResponse(**session)

    def delete_task(self, task_id: str) -> bool:
        """Delete task session file."""
        path = self._get_session_path(task_id)
        if path.exists():
            with self._lock:
                path.unlink()
            return True
        return False

    def task_exists(self, task_id: str) -> bool:
        """Check if task exists."""
        return self._get_session_path(task_id).exists()
