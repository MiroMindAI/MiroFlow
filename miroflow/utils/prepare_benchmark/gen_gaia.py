# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import pathlib
import shutil
from typing import Generator, MutableMapping

from datasets import load_dataset
from huggingface_hub import hf_hub_download

from .common import Task


def download_file(hf_token: str, file_path: str, data_dir: str, task_id: str) -> str:
    """Download a file from HuggingFace and save it to the local data directory.

    Args:
        hf_token: HuggingFace token for authentication
        file_path: The relative file path in the HuggingFace dataset (e.g., '2023/validation/xxx.xlsx')
        data_dir: The local data directory
        task_id: The task ID (used for organizing files)

    Returns:
        The absolute path to the downloaded file, or None if download fails
    """
    if not file_path:
        return None

    try:
        # Download from HuggingFace hub (returns cached path)
        cached_path = hf_hub_download(
            repo_id="gaia-benchmark/GAIA",
            filename=file_path,
            repo_type="dataset",
            token=hf_token,
        )

        # Get the file extension from the original path
        original_ext = pathlib.Path(file_path).suffix

        # Ensure data_dir is absolute and resolved
        data_dir_path = pathlib.Path(data_dir).resolve()
        files_dir = data_dir_path / "gaia-val" / "files"
        files_dir.mkdir(parents=True, exist_ok=True)

        # Create local file path with task_id as filename
        local_path = files_dir / f"{task_id}{original_ext}"

        # Copy from cache to local directory
        shutil.copy2(cached_path, local_path)

        return str(local_path)

    except Exception as e:
        print(f"Warning: Failed to download file for task {task_id}: {e}")
        return None


def gen_gaia_validation(hf_token: str, data_dir: str) -> Generator[Task, None, None]:
    """Generate GAIA validation tasks with downloaded files.

    Args:
        hf_token: HuggingFace token for authentication
        data_dir: The local data directory for storing files

    Yields:
        Task objects with local file paths
    """
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
        metadata.pop("file_name")  # Remove but don't use

        # Download the file if it exists
        local_file_path = None
        if file_path:
            local_file_path = download_file(hf_token, file_path, data_dir, task_id)

        task = Task(
            task_id=task_id,
            task_question=question,
            ground_truth=gt,
            file_path=local_file_path,
            metadata=metadata,
        )
        yield task

    return
