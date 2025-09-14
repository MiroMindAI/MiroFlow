# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Generator, MutableMapping

from datasets import load_dataset

from utils.prepare_benchmark.common import Task


def check_file(file_path: str, file_name: str):
    if file_path == "":
        return None, False
    return file_path, True


def gen_gaia_validation(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset(
        "gaia-benchmark/GAIA",
        name="2023_all",
        token=hf_token,
        split="validation",
    )
    for x in dataset:
        metadata: MutableMapping = x  # type: ignore
        task_id = metadata.pop("task_id")
        question = metadata.pop("Question")
        gt = metadata.pop("Final answer")
        file_path = metadata.pop("file_path")
        file_name = metadata.pop("file_name")
        uri, exists = check_file(file_path, file_name)
        task = Task(
            task_id=task_id,
            task_question=question,
            ground_truth=gt,
            file_path=None if not exists else uri,
            metadata=metadata,
        )
        yield task

    return
