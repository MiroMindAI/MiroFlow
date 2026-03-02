# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
File content preprocessor for processing task-associated files.

This processor reads file content and appends it to the task description,
matching the behavior of MiroThinker's input_handler.py.
"""

import os

from miroflow.agents.context import AgentContext
from miroflow.io_processor.base import BaseIOProcessor
from miroflow.registry import ComponentType, register
from miroflow.utils.file_content_utils import process_file_content


@register(ComponentType.IO_PROCESSOR, "FileContentPreprocessor")
class FileContentPreprocessor(BaseIOProcessor):
    """
    File content preprocessor.

    Reads the associated file, converts its content to text/markdown,
    and appends it to the task_description. This matches the behavior
    of MiroThinker's input_handler.py.

    After processing:
    - task_description: Updated with file content appended
    - task_file_name: Cleared to prevent duplicate processing by InputMessageGenerator
    - file_content_preprocessed: Set to True to indicate processing occurred
    """

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        task_description = ctx.get("task_description", "")
        task_file_name = ctx.get("task_file_name", "")

        if not task_file_name or not task_file_name.strip():
            # No file to process
            return {}

        # Get OpenAI configuration for media (image/audio/video) processing
        openai_api_key = ctx.get("openai_api_key") or os.environ.get("OPENAI_API_KEY")
        openai_base_url = ctx.get("openai_base_url") or os.environ.get(
            "OPENAI_BASE_URL", "https://api.openai.com/v1"
        )

        print(f"FileContentPreprocessor: Processing file '{task_file_name}'")

        # Process file content using the utility function
        updated_task_description = process_file_content(
            task_description=task_description,
            task_file_name=task_file_name,
            openai_api_key=openai_api_key,
            openai_base_url=openai_base_url,
        )

        print("FileContentPreprocessor: File content appended to task_description")

        return {
            "task_description": updated_task_description,
            "task_file_name": "",  # Clear to prevent InputMessageGenerator from adding file path prompt
            "file_content_preprocessed": True,
        }
