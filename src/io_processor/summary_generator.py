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
            ),
        )

        # Skip blind guessing: when agent hit max turns/context limit and
        # this is NOT the final retry, skip answer generation to avoid wasting
        # the retry on a low-confidence guess. Let ExceedMaxTurnSummaryGenerator
        # produce a failure experience summary for the next retry instead.
        reached_limit = ctx.get("reached_limit", False)
        is_final_retry = ctx.get("is_final_retry", False)
        if reached_limit and not is_final_retry:
            return AgentContext(
                summary_prompt=prompt,
                summary="Task incomplete - skipping answer generation to retry with failure experience.",
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
