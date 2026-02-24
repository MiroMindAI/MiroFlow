# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
输入提示生成器 - 生成任务提示
"""

from src.io_processor.base import BaseIOProcessor
from src.agents.context import AgentContext
from src.registry import register, ComponentType


@register(ComponentType.IO_PROCESSOR, "InputHintGenerator")
class InputHintGenerator(BaseIOProcessor):
    """输入提示生成器"""

    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "prompt")

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        prompt = self.prompt_manager.render_prompt(
            "hint_generation_prompt",
            context=dict(
                task_description=ctx.get("task_description"),
            ),
        )
        task_hint = await self.llm_client.create_message(prompt)
        return {"task_hint": task_hint.response_text}
