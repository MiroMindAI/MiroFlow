# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Task management endpoints."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from ...core.session_manager import SessionManager
from ...core.task_executor import TaskExecutor
from ...models.task import (
    FileInfo,
    Message,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
)
from ..dependencies import get_session_manager, get_task_executor

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", response_model=TaskResponse)
async def create_task(
    task: TaskCreate,
    session_manager: SessionManager = Depends(get_session_manager),
    task_executor: TaskExecutor = Depends(get_task_executor),
) -> TaskResponse:
    """Create and start a new task."""
    task_id = f"task_{uuid.uuid4().hex[:12]}"

    # Get file info if provided
    file_info = None
    if task.file_id:
        # Look up the uploaded file
        from ...core.config import config

        upload_dir = config.uploads_dir / task.file_id
        if upload_dir.exists():
            files = list(upload_dir.iterdir())
            if files:
                file_path = files[0]
                ext = file_path.suffix.lower()
                from .uploads import FILE_TYPE_MAP

                file_info = FileInfo(
                    file_id=task.file_id,
                    file_name=file_path.name,
                    file_type=FILE_TYPE_MAP.get(ext, "File"),
                    absolute_file_path=str(file_path.absolute()),
                )

    # Create session
    task_response = session_manager.create_task(
        task_id=task_id,
        task_description=task.task_description,
        config_path=task.config_path,
        file_info=file_info,
    )

    # Submit for background execution
    task_executor.submit_task(
        task_id=task_id,
        task_description=task.task_description,
        config_path=task.config_path,
        file_info=file_info,
    )

    return task_response


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session_manager: SessionManager = Depends(get_session_manager),
) -> TaskListResponse:
    """List all tasks with pagination."""
    tasks, total = session_manager.list_tasks(page, page_size)
    return TaskListResponse(
        tasks=tasks,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    task_executor: TaskExecutor = Depends(get_task_executor),
) -> TaskResponse:
    """Get task by ID with current progress."""
    task = session_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # If running, get progress from executor
    if task.status == "running":
        progress = task_executor.get_task_progress(task_id)
        task = session_manager.update_task(task_id, progress)
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")

    return task


@router.get("/{task_id}/status", response_model=TaskStatusUpdate)
async def get_task_status(
    task_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    task_executor: TaskExecutor = Depends(get_task_executor),
) -> TaskStatusUpdate:
    """Lightweight status endpoint for polling."""
    task = session_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    progress: dict = {}
    if task.status == "running":
        progress = task_executor.get_task_progress(task_id)
        # Update session with progress
        session_manager.update_task(
            task_id,
            {
                "current_turn": progress.get("current_turn", 0),
                "step_count": progress.get("step_count", 0),
            },
        )

    # Convert messages to Message objects
    messages = [Message(**m) for m in progress.get("messages", [])]

    return TaskStatusUpdate(
        id=task.id,
        status=task.status,
        current_turn=progress.get("current_turn", task.current_turn),
        step_count=progress.get("step_count", task.step_count),
        recent_logs=progress.get("recent_logs", []),
        messages=messages,
        final_answer=task.final_answer,
        summary=task.summary,
        error_message=task.error_message,
    )


@router.delete("/{task_id}")
async def delete_task(
    task_id: str,
    session_manager: SessionManager = Depends(get_session_manager),
    task_executor: TaskExecutor = Depends(get_task_executor),
) -> dict[str, str]:
    """Delete a task. Cancels if running."""
    task = session_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Cancel if running
    if task.status == "running":
        task_executor.cancel_task(task_id)

    # Delete session
    session_manager.delete_task(task_id)

    return {"message": "Task deleted", "id": task_id}
