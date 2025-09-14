# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
https://raw.githubusercontent.com/RUC-NLPIR/WebThinker/refs/heads/main/data/GAIA/dev.json
"""

import json
from typing import Generator, MutableMapping

import requests

from utils.prepare_benchmark.common import Task


def gen_gaia_text_only() -> Generator[Task, None, None]:
    response = requests.get(
        "https://raw.githubusercontent.com/RUC-NLPIR/WebThinker/refs/heads/main/data/GAIA/dev.json"
    )
    dataset = json.loads(response.content)
    for row in dataset:
        metadata: MutableMapping = row
        task_id = metadata.pop("task_id", "")
        question = metadata.pop("Question", "")
        answer = metadata.pop("answer", "")
        task = Task(
            task_id=task_id,
            task_question=question,
            ground_truth=answer,
            file_path=None,
            metadata=metadata,
        )
        yield task
    return
