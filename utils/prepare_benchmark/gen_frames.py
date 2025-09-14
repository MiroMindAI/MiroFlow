# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Generator, MutableMapping

from datasets import load_dataset

from utils.prepare_benchmark.common import Task


def gen_frames_test(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset(
        "google/frames-benchmark",
        token=hf_token,
        split="test",
    )
    for x in dataset:
        task = x
        metadata: MutableMapping = x  # type: ignore
        task_id = metadata.pop("Unnamed: 0", "")
        question = metadata.pop("Prompt", "")
        answer = metadata.pop("Answer", "")
        task = Task(
            task_id=str(task_id),
            task_question=question,
            ground_truth=answer,
            metadata=metadata,
        )
        yield task
    return
