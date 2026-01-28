# SPDX-FileCopyrightText: 2025 MiromindAI
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import json
import os
import threading
import time
import uuid
import contextvars
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
from dataclasses import dataclass
from pydantic import BaseModel, Field
from .span import Span

# -------------------------------------------------------------------------
# Utilities
# -------------------------------------------------------------------------


def utc_iso(ts: Optional[float] = None) -> str:
    if ts is None:
        ts = time.time()
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ensure_jsonable(x: Any) -> Any:
    """Best-effort JSON conversion. Never raise."""
    try:
        json.dumps(x, ensure_ascii=False)
        return x
    except Exception:
        try:
            return str(x)
        except Exception:
            return "<unserializable>"


# -------------------------------------------------------------------------
# Context Management
# -------------------------------------------------------------------------


@dataclass(frozen=True)
class TaskContextVar:
    task_id: str
    attempt_id: int
    retry_id: int

    def __repr__(self) -> str:
        return f"task_{self.task_id}_attempt_{self.attempt_id}_retry_{self.retry_id}"


# 使用默认对象代替 None，避免后续大量的 None check
ROOT_CONTEXT = TaskContextVar(task_id="root", attempt_id=0, retry_id=0)

CURRENT_TASK_CONTEXT_VAR: contextvars.ContextVar[TaskContextVar] = (
    contextvars.ContextVar("CURRENT_TASK_CONTEXT_VAR", default=ROOT_CONTEXT)
)


def set_current_task_context_var(task_context_var: TaskContextVar):
    return CURRENT_TASK_CONTEXT_VAR.set(task_context_var)


def reset_current_task_context_var(token):
    CURRENT_TASK_CONTEXT_VAR.reset(token)


def get_current_task_context_var() -> TaskContextVar:
    return CURRENT_TASK_CONTEXT_VAR.get()


# -------------------------------------------------------------------------
# Data Models (Pydantic)
# -------------------------------------------------------------------------


class TaskMeta(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    attempt_id: int = 1
    retry_id: int = 0
    task_description: str = ""
    task_file_name: Optional[str] = None

    status: Literal["pending", "running", "completed", "interrupted", "failed"] = (
        "pending"
    )
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    final_boxed_answer: str = ""
    judge_result: str = ""
    error: Optional[str] = None
    ground_truth: Optional[str] = None

    is_valid_box: Optional[bool] = None
    exceed_max_turn_summary: Optional[str] = None
    used_exceed_max_turn_summaries: bool = False
    previous_retry_ids: List[int] = Field(default_factory=list)

    updated_at: str = Field(default_factory=utc_iso)


class AgentStateEntry(BaseModel):
    updated_at: str = Field(default_factory=utc_iso)
    state: Dict[str, Any] = Field(default_factory=dict)


class TaskLogFile(BaseModel):
    """Represents the structure of the JSON log file."""

    task_meta: TaskMeta = Field(default_factory=TaskMeta)
    current_span: Optional[Span] = None
    agent_states: Dict[str, AgentStateEntry] = Field(default_factory=dict)
    step_logs: list[Dict[str, Any]] = Field(default_factory=list)


# -------------------------------------------------------------------------
# Tracer Implementation
# -------------------------------------------------------------------------


class TaskTracer:
    """
    Thread-safe, singleton-friendly tracer that manages logs per TaskContext.
    """

    def __init__(self, log_path: str | Path = "./logs"):
        self.log_path = Path(log_path)
        if not self.log_path.exists():
            self.log_path.mkdir(parents=True, exist_ok=True)

        self._active_tasks: Dict[str, TaskLogFile] = {}

        # 序列号追踪：Key -> int
        self._seq_map: Dict[str, int] = {}

        # 锁：保护 _active_tasks 和 _seq_map 的并发修改
        self._data_lock = threading.Lock()

        # 锁：保护文件写入，防止多线程写同一个文件导致错乱
        # (虽然这里使用了 key 隔离文件，但为了防止原子重命名冲突，保留一个 IO 锁是个好习惯，或者针对每个文件锁)
        # 这里为了简单高效，假设不同 task 写不同文件，IO 不互斥。
        pass

    def set_log_path(self, log_path: Path | str) -> None:
        self.log_path = Path(log_path)
        if not self.log_path.exists():
            self.log_path.mkdir(parents=True, exist_ok=True)

    # ---------- Internal Helpers ----------

    def _get_context_key(self) -> str:
        """从 ContextVars 获取当前任务的唯一标识字符串"""
        ctx = get_current_task_context_var()
        return str(ctx)

    def _get_or_create_log(self, key: str) -> TaskLogFile:
        """调用方必须持有 self._data_lock"""
        if key not in self._active_tasks:
            self._active_tasks[key] = TaskLogFile()
            self._seq_map[key] = 0
            # 同步 meta 中的 ID 信息 (可选)
            # self._active_tasks[key].task_meta.task_id = ...
        return self._active_tasks[key]

    def _flush_to_disk(self, key: str, log_obj: TaskLogFile):
        """将对象序列化并写入磁盘。执行原子写入 (Write-Replace)。"""
        if not key:
            return

        try:
            payload = log_obj.model_dump_json(indent=2)
        except Exception as e:
            print(f"Error serializing log for {key}: {e}")
            return

        file_path = self.log_path / f"{key}.json"
        temp_path = self.log_path / f"{key}.tmp"

        # 2. 写入临时文件然后重命名，保证原子性
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(payload)
            os.replace(temp_path, file_path)
        except Exception as e:
            print(f"Error writing log file {file_path}: {e}")

    def flush(self):
        """
        手动刷新当前任务的日志到磁盘。
        """
        key = self._get_context_key()

        with self._data_lock:
            if key in self._active_tasks:
                # 浅拷贝模型对象用于序列化，尽量减少锁持有时间
                # 注意：如果模型很深，这里可能需要 model_copy(deep=True)
                # 但为了性能，通常直接序列化即可，因为单线程内通常不会竞争修改
                log_obj = self._active_tasks[key]
                # 在锁内不能做 IO，但可以做数据的快照。
                # 简单起见，我们在锁内拿到引用，在锁外 dump (虽然有极小概率读取到修改中的数据，但在 logger 场景可接受)
                pass
            else:
                return

        # 执行 IO
        self._flush_to_disk(key, log_obj)

    # ---------- Lifecycle ----------

    def start(self) -> None:
        key = self._get_context_key()
        with self._data_lock:
            log_file = self._get_or_create_log(key)
            log_file.task_meta.status = "running"
            log_file.task_meta.start_time = utc_iso()
            log_file.task_meta.updated_at = utc_iso()

        self.flush()

    # todo: 这里的interrupted有被使用吗？
    def finish(
        self,
        status: Literal["completed", "interrupted", "failed"] = "completed",
        *,
        error: Optional[str] = None,
    ) -> None:
        key = self._get_context_key()

        # 1. 更新最终状态
        with self._data_lock:
            if key not in self._active_tasks:
                return  # 甚至没开始过

            log_file = self._active_tasks[key]
            log_file.task_meta.status = status
            log_file.task_meta.end_time = utc_iso()
            log_file.task_meta.updated_at = utc_iso()
            if error is not None:
                log_file.task_meta.error = error

        # 2. 最后一次强制 Flush
        if key in self._active_tasks:
            self._flush_to_disk(key, self._active_tasks[key])

        # 3. [关键修复] 清理内存，防止内存泄漏
        with self._data_lock:
            if key in self._active_tasks:
                del self._active_tasks[key]
            if key in self._seq_map:
                del self._seq_map[key]

    # ---------- Meta & State ----------

    def update_task_meta(self, patch: Dict[str, Any]) -> None:
        key = self._get_context_key()
        with self._data_lock:
            log_file = self._get_or_create_log(key)
            for k, v in patch.items():
                if hasattr(log_file.task_meta, k):
                    setattr(log_file.task_meta, k, _ensure_jsonable(v))
            log_file.task_meta.updated_at = utc_iso()
        self.flush()

    def save_agent_states(self, node_name: str, states: Dict[str, Any]) -> None:
        key = self._get_context_key()
        with self._data_lock:
            log_file = self._get_or_create_log(key)
            log_file.agent_states[node_name] = AgentStateEntry(
                updated_at=utc_iso(),
                state=_ensure_jsonable(states),
            )
        self.flush()

    def set_current_span(self, current_span: Span) -> None:
        key = self._get_context_key()
        with self._data_lock:
            log_file = self._get_or_create_log(key)
            log_file.current_span = (
                current_span  # 假设 Span 是 Pydantic model 或 jsonable
            )
        self.flush()

    # ---------- Logging ----------

    def append_step_event(self, event: Dict[str, Any]) -> None:
        key = self._get_context_key()
        ev = dict(event)
        ev.setdefault("ts", utc_iso())

        with self._data_lock:
            log_file = self._get_or_create_log(key)

            # 生成递增序号
            self._seq_map[key] += 1
            ev["seq"] = self._seq_map[key]

            log_file.step_logs.append(_ensure_jsonable(ev))

        # 每次 log 都 flush 在高频场景下性能较差
        # 如果追求极致性能，可以设定阈值或只在 finish 时 flush
        # 这里为了数据安全性保持 flush
        self.flush()

    def log(
        self,
        msg: str,
        *,
        level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO",
        span_id: Optional[str] = None,
        node_id: Optional[str] = None,
        step_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None,
        where: Optional[Dict[str, Any]] = None,
    ) -> None:
        payload = {"type": f"log_{level.lower()}", "msg": msg}
        # 仅添加非空字段，保持日志整洁
        if span_id:
            payload["span_id"] = span_id
        if node_id:
            payload["node_id"] = node_id
        if step_id:
            payload["step_id"] = step_id
        if data:
            payload["data"] = data
        if where:
            payload["where"] = where

        self.append_step_event(payload)

    def debug(self, msg: str, **kwargs) -> None:
        self.log(msg, level="DEBUG", **kwargs)

    def info(self, msg: str, **kwargs) -> None:
        self.log(msg, level="INFO", **kwargs)

    def warning(self, msg: str, **kwargs) -> None:
        self.log(msg, level="WARNING", **kwargs)

    def error(self, msg: str, **kwargs) -> None:
        self.log(msg, level="ERROR", **kwargs)


# -------------------------------------------------------------------------
# Singleton Management
# -------------------------------------------------------------------------

_SINGLETON_LOCK = threading.Lock()
_SINGLETON: Optional[TaskTracer] = None


def set_tracer(log_path: Path):
    global _SINGLETON
    with _SINGLETON_LOCK:
        if _SINGLETON is None:
            _SINGLETON = TaskTracer(log_path)
        else:
            _SINGLETON.set_log_path(log_path)


def get_tracer() -> TaskTracer:
    global _SINGLETON
    if _SINGLETON is None:
        with _SINGLETON_LOCK:
            # Double-check locking
            if _SINGLETON is None:
                _SINGLETON = TaskTracer()
    return _SINGLETON
