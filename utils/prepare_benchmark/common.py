# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import dataclasses
import json
from typing import Any, MutableMapping


@dataclasses.dataclass
class Task:
    """Generic benchmark task data structure"""

    task_id: str
    task_question: str
    ground_truth: str
    file_path: str | None = None
    metadata: MutableMapping[str, Any] = dataclasses.field(default_factory=dict)

    def to_json(self) -> bytes:
        return json.dumps(dataclasses.asdict(self), ensure_ascii=False).encode()

    @classmethod
    def from_json(cls, b: bytes):
        obj = json.loads(b.decode())
        return cls(**obj)
