# SPDX-FileCopyrightText: 2024 OpenAI
# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0
# SPDX-License-Identifier: MIT
"""
adapted from simple-eval repo:
https://github.com/openai/simple-evals/blob/ee3b0318d8d1d9d72755a4120879be65f7c07e9e/browsecomp_eval.py#L50
"""

import base64
import hashlib
from typing import Generator, MutableMapping

from datasets import load_dataset

from common import Task


def derive_key(password: str, length: int) -> bytes:
    """Derive a fixed-length key from the password using SHA256."""
    hasher = hashlib.sha256()
    hasher.update(password.encode())
    key = hasher.digest()
    return key * (length // len(key)) + key[: length % len(key)]


def decrypt(ciphertext_b64: str, password: str) -> str:
    """Decrypt base64-encoded ciphertext with XOR."""
    encrypted = base64.b64decode(ciphertext_b64)
    key = derive_key(password, len(encrypted))
    decrypted = bytes(a ^ b for a, b in zip(encrypted, key))
    return decrypted.decode("utf-8")


def gen_browsecomp_test(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset(
        "smolagents/browse_comp",
        token=hf_token,
        split="test",
    )
    for idx, x in enumerate(dataset):
        metadata: MutableMapping = x
        problem_encrypted = metadata.pop("problem")
        answer_encrypted = metadata.pop("answer")
        canary = metadata.pop("canary")
        task = Task(
            task_id=str(idx),
            task_question=decrypt(problem_encrypted, canary),
            ground_truth=decrypt(answer_encrypted, canary),
            file_path=None,
            metadata=metadata,
        )
        yield task
    return


def gen_browsecomp_zh_test(hf_token: str) -> Generator[Task, None, None]:
    dataset = load_dataset(
        "PALIN2018/BrowseComp-ZH",
        token=hf_token,
        split="test",
    )
    for idx, x in enumerate(dataset):
        metadata: MutableMapping = x
        problem_encrypted = metadata.pop("Question")
        answer_encrypted = metadata.pop("Answer")
        canary = metadata.pop("canary")
        metadata["Topic"] = decrypt(metadata["Topic"], canary)
        task = Task(
            task_id=str(idx),
            task_question=decrypt(problem_encrypted, canary),
            ground_truth=decrypt(answer_encrypted, canary),
            file_path=None,
            metadata=metadata,
        )
        yield task
    return
