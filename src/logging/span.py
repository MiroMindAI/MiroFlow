# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
import time
import uuid


def new_id(prefix: str = "") -> str:
    core = uuid.uuid4().hex[:16]
    return f"{prefix}{core}" if prefix else core


@dataclass
class Span:
    span_id: str
    name: str
    parent_span_id: Optional[str]
    task_id: Optional[str] = None
    attempt_id: Optional[int] = None
    retry_id: Optional[int] = None

    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None
    status: str = "ok"  # ok | error
    attrs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None

    def end(self) -> None:
        self.end_ts = time.time()

    @property
    def duration_ms(self) -> Optional[int]:
        if self.end_ts is None:
            return None
        return int((self.end_ts - self.start_ts) * 1000)
