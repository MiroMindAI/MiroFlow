# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Input message generator - generates initial user messages and system prompts
"""

import os
import datetime

from miroflow.io_processor.base import BaseIOProcessor
from miroflow.agents.context import AgentContext
from miroflow.registry import register, ComponentType
from miroflow.utils.io_utils import get_file_type


@register(ComponentType.IO_PROCESSOR, "InputMessageGenerator")
class InputMessageGenerator(BaseIOProcessor):
    """Input message generator"""

    USE_PROPAGATE_MODULE_CONFIGS = ("prompt",)

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        task_file_name = ctx.get("task_file_name")
        if task_file_name is not None and task_file_name.strip():
            task_file_type = get_file_type(task_file_name)
            file_input = dict(
                file_type=task_file_type,
                file_name=task_file_name,
                absolute_file_path=os.path.abspath(task_file_name),
            )
        else:
            file_input = None

        initial_user_message = self.prompt_manager.render_prompt(
            prompt_name="initial_user_text",
            context=dict(
                task_description=ctx.get("task_description"),
                file_input=file_input,
                task_hint=ctx.get("task_hint", None),
            ),
        )

        system_prompt = self.prompt_manager.render_prompt(
            prompt_name="system_prompt",
            context=dict(
                formatted_date=datetime.datetime.now().strftime("%Y-%m-%d"),
                mcp_server_definitions=ctx.get("mcp_server_definitions", None),
            ),
        )

        return {
            "system_prompt": system_prompt,
            "initial_user_message": initial_user_message,
        }
