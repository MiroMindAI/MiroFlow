# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
摘要生成器 - 从对话历史生成摘要
"""

from src.io_processor.base import BaseIOProcessor
from src.agents.context import AgentContext
from src.registry import register, ComponentType
from src.llm.base import ContextLimitError


@register(ComponentType.IO_PROCESSOR, "SummaryGenerator")
class SummaryGenerator(BaseIOProcessor):
    """摘要生成器"""

    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "prompt")

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        prompt = self.prompt_manager.render_prompt(
            "summarize_prompt",
            context=dict(
                task_description=ctx.get("task_description"),
                task_failed=ctx.get("task_failed", False),
                chinese_context=self.cfg.get("chinese_context", False),
            ),
        )

        message_history = ctx.get("message_history", [])
        try:
            llm_response = await self.llm_client.create_message(
                message_history=message_history
                + [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
            )
        except ContextLimitError:
            return AgentContext(
                summary_prompt=prompt,
                summary="Task interrupted due to context limit.",
            )

        # Return both summary_prompt and summary in agent state
        return AgentContext(summary_prompt=prompt, summary=llm_response.response_text)
