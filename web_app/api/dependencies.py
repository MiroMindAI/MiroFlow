# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""FastAPI dependencies for dependency injection."""

from ..core.config import AppConfig, config
from ..core.session_manager import SessionManager
from ..core.task_executor import TaskExecutor

# Global instances (created once at startup)
_session_manager: SessionManager | None = None
_task_executor: TaskExecutor | None = None


def get_config() -> AppConfig:
    """Get application configuration."""
    return config


def get_session_manager() -> SessionManager:
    """Get session manager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(config.sessions_dir)
    return _session_manager


def get_task_executor() -> TaskExecutor:
    """Get task executor instance."""
    global _task_executor
    if _task_executor is None:
        _task_executor = TaskExecutor(config, get_session_manager())
    return _task_executor


def init_dependencies() -> None:
    """Initialize all dependencies at startup."""
    global _session_manager, _task_executor
    _session_manager = SessionManager(config.sessions_dir)
    _task_executor = TaskExecutor(config, _session_manager)
