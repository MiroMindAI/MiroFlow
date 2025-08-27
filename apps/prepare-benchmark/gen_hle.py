# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import base64
import pathlib
from typing import Generator, MutableMapping

from datasets import load_dataset

from common import Task


def save_image(image, data_dir: str, task_id: str) -> str:
    if not image:
        return None
    # Ensure data_dir is absolute and resolved to avoid ugly .. in the path
    data_dir_path = pathlib.Path(data_dir).resolve()
    image_path = data_dir_path / "hle" / "images" / f"{task_id}.png"
    image_path.parent.mkdir(parents=True, exist_ok=True)

    # Handle different image formats
    if isinstance(image, str):
        # If it's a data URL, extract the base64 part
        if image.startswith("data:"):
            try:
                header, b64data = image.split(",", 1)
                image_data = base64.b64decode(b64data)
                image_path.write_bytes(image_data)
            except Exception as e:
                raise ValueError(
                    f"Cannot process image data:<class 'str'> (data URL): {e}"
                )
        else:
            try:
                image_data = base64.b64decode(image)
                image_path.write_bytes(image_data)
            except Exception as e:
                raise ValueError(
                    f"Cannot process image data:<class 'str'> (raw b64): {e}"
                )
    elif hasattr(image, "save"):
        # If it's a PIL Image object
        image.save(image_path)
    else:
        # Try to handle it as bytes directly
        try:
            image_path.write_bytes(image)
        except Exception:
            raise ValueError(f"Cannot process image data: {type(image)}")

    return str(image_path)


def gen_hle_test(hf_token: str, data_dir: str) -> Generator[Task, None, None]:
    dataset = load_dataset("cais/hle", split="test", token=hf_token)
    for x in dataset:
        metadata: MutableMapping = x  # type: ignore
        task_id = metadata.pop("id")
        question = metadata.pop("question")
        gt = metadata.pop("answer")
        image = metadata.pop("image")  # base64 encoded image
        image_uri = save_image(image, data_dir, task_id)
        metadata.pop("image_preview")
        metadata.pop("rationale_image")
        task = Task(
            task_id=task_id,
            task_question=question,
            ground_truth=gt,
            file_path=image_uri,
            metadata=metadata,
        )
        yield task

    return
