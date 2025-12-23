# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

import copy
import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Literal, Optional
from .span import Span

from pydantic import BaseModel, Field, PrivateAttr

from .logger import bootstrap_logger

LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


def utc_iso(ts: Optional[float] = None) -> str:
    if ts is None:
        ts = time.time()
    dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _ensure_jsonable(x: Any) -> Any:
    """Best-effort JSON conversion. Never raise."""
    try:
        # Fast path
        json.dumps(x, ensure_ascii=False)
        return x
    except Exception:
        try:
            return str(x)
        except Exception:
            return "<unserializable>"


class TaskMeta(BaseModel):
    task_id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:12]}")
    run_id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:12]}")
    task_name: str = ""
    task_file_name: Optional[str] = None

    status: Literal["pending", "running", "completed", "interrupted", "failed"] = "pending"
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    final_boxed_answer: str = ""
    judge_result: str = ""
    error: Optional[str] = None

    updated_at: str = Field(default_factory=utc_iso)


class AgentStateEntry(BaseModel):
    #step_id: Optional[int] = None
    updated_at: str = Field(default_factory=utc_iso)
    # 全量状态（你强调可恢复性）
    state: Dict[str, Any] = Field(default_factory=dict)


class TaskLogFile(BaseModel):
    task_meta: TaskMeta = Field(default_factory=TaskMeta)
    current_span: Span = Field(default_factory=Span)

    # 最新状态：node_id -> AgentStateEntry
    agent_states: Dict[str, AgentStateEntry] = Field(default_factory=dict)

    # 时间线：span + 手写 log（混在一起）
    step_logs: list[Dict[str, Any]] = Field(default_factory=list)


class TaskTracer(BaseModel):
    """
    Single-file JSON task log with 4 sections:
      - agent_states (latest-only map)
      - step_logs (append list; span+log mixed)
      - meta (latest)
      - heartbeat.current_span (latest-only)

    Every update does an atomic flush to the same JSON file.
    """

    log_path: Path
    data: TaskLogFile = Field(default_factory=TaskLogFile)

    _lock: threading.Lock = PrivateAttr(default_factory=threading.Lock)
    _seq: int = PrivateAttr(default=0)  # stable ordering within step_logs

    class Config:
        arbitrary_types_allowed = True

    # ---------- lifecycle ----------
    def start(self) -> None:
        self.data.task_meta.status = "running"
        self.data.task_meta.start_time = utc_iso()
        self._touch_meta()
        self.flush()

    def finish(
        self,
        status: Literal["completed", "interrupted", "failed"] = "completed",
        *,
        error: Optional[str] = None,
    ) -> None:
        self.data.task_meta.status = status
        self.data.task_meta.end_time = utc_iso()
        if error is not None:
            self.data.task_meta.error = error
        self._touch_meta()
        self.flush()

    # ---------- meta ----------
    def update_task_meta(self, patch: Dict[str, Any]) -> None:
        for k, v in patch.items():
            if hasattr(self.data.task_meta, k):
                setattr(self.data.task_meta, k, _ensure_jsonable(v))
        self._touch_meta()
        self.flush()

    def _touch_meta(self) -> None:
        self.data.task_meta.updated_at = utc_iso()

    # ---------- heartbeat ----------
    def set_current_span(self, current_span: Span) -> None:
        self.data.current_span = copy.deepcopy(current_span)
        self.flush()

    def clear_current_span(self) -> None:
        self.data.current_span = Span()
        self.flush()

    # ---------- agent states (latest-only) ----------
    def save_agent_states(
        self,
        node_name: str,
        states: Dict[str, Any],
    ) -> None:
        self.data.agent_states[node_name] = AgentStateEntry(
            #step_id=step_id,
            updated_at=utc_iso(),
            state=_ensure_jsonable(states),
        )
        self.flush()

    # ---------- step logs (time line) ----------
    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def append_step_event(self, event: Dict[str, Any]) -> None:
        """
        Append an event into step_logs (span_start/span_end/log/etc).
        Always adds ts + seq.
        """
        ev = dict(event)
        ev.setdefault("ts", utc_iso())
        ev.setdefault("seq", self._next_seq())
        self.data.step_logs.append(_ensure_jsonable(ev))
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
        self.append_step_event(
            {
                "type": "log",
                "level": level,
                "msg": msg,
                "span_id": span_id,
                "node_id": node_id,
                "step_id": step_id,
                "where": where,
                "data": data or {},
            }
        )

    # ---------- IO: single-file atomic flush ----------
    def flush(self) -> None:
        """
        Persist whole JSON file atomically.
        Never raise.
        """
        try:
            with self._lock:
                self._flush_locked()
        except Exception as e:
            logger.error(e, stack_info=True, exc_info=True)

    def _flush_locked(self) -> None:
        # Ensure directory
        try:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        tmp_path = self.log_path.with_suffix(self.log_path.suffix + ".tmp")
        payload = self.data.model_dump(mode="json")

        # atomic replace
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.log_path)

import contextvars

CURRENT_TASK_TRACER: contextvars.ContextVar[Optional[TaskTracer]] = contextvars.ContextVar(
    "CURRENT_TASK_TRACER", default=None
)

def set_current_tracer(tracer: TaskTracer):
    return CURRENT_TASK_TRACER.set(tracer)

def reset_current_tracer(token):
    CURRENT_TASK_TRACER.reset(token)

def get_tracer() -> Optional[TaskTracer]:
    return CURRENT_TASK_TRACER.get()