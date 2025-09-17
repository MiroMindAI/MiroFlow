# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import base64
from typing import Generator, MutableMapping

from datasets import load_dataset

from utils.prepare_benchmark.common import Task


def xor_decrypt(data, key):
    """
    XOR decrypt data with a key
    """
    key_bytes = key.encode('utf-8')
    key_length = len(key_bytes)
    return bytes([data[i] ^ key_bytes[i % key_length] for i in range(len(data))])

def gen_xbench_ds(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset(
        "xbench/DeepSearch",
        split="train",
    )
    for x in dataset:
        metadata: MutableMapping = x  # type: ignore
        task_id = metadata.pop("id")

        key = metadata.pop("canary")
        prompt = xor_decrypt(base64.b64decode(metadata.pop("prompt")), key).decode('utf-8')
        answer = xor_decrypt(base64.b64decode(metadata.pop("answer")), key).decode('utf-8')
        reference_steps = xor_decrypt(base64.b64decode(metadata.pop("reference_steps")), key).decode('utf-8')
        task = Task(
            task_id=task_id,
            task_question=prompt,
            ground_truth=answer,
            file_path=None,
            metadata={"reference_steps": reference_steps},
        )
        yield task

    return
