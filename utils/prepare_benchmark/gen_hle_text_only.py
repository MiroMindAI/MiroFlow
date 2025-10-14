# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Generator, MutableMapping

from datasets import load_dataset

from utils.prepare_benchmark.common import Task


def gen_hle_text_only(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset("macabdul9/hle_text_only", split="test", token=hf_token)
    for x in dataset:
        metadata: MutableMapping = x  # type: ignore
        task_id = metadata.pop("id")
        question = metadata.pop("question")
        gt = metadata.pop("answer")
        metadata.pop("image_preview")
        metadata.pop("rationale_image")
        task = Task(
            task_id=task_id,
            task_question=question,
            ground_truth=gt,
            file_path=None,
            metadata=metadata,
        )
        yield task

    return
