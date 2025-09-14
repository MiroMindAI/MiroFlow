# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Generator, MutableMapping

from datasets import load_dataset

from utils.prepare_benchmark.common import Task


def gen_webwalkerqa(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset(
        "callanwu/WebWalkerQA",
        token=hf_token,
        split="main",
    )
    for idx, x in enumerate(dataset):
        metadata: MutableMapping = x
        question = metadata.pop("question", "")
        answer = metadata.pop("answer", "")
        # root_url = metadata.pop("root_url", "")
        task = Task(
            task_id=str(idx),
            task_question=question,
            ground_truth=answer,
            # TODO: maybe put root url_here???
            file_path=None,
            metadata=metadata,
        )
        yield task
    return
