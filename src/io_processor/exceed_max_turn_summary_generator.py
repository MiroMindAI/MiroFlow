# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Exceed Max Turn Summary Generator - generates summaries when task exceeds max turns without valid box.
"""

from src.agents.context import AgentContext
from src.io_processor.base import BaseIOProcessor
from src.registry import ComponentType, register


@register(ComponentType.IO_PROCESSOR, "ExceedMaxTurnSummaryGenerator")
class ExceedMaxTurnSummaryGenerator(BaseIOProcessor):
    """Generates summaries for retry logic when task exceeds max turns without valid box."""

    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "prompt")

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        prompt = self.prompt_manager.render_prompt(
            "exceed_max_turn_summary_prompt",
            context=dict(
                task_description=ctx.get("task_description"),
                summary=ctx.get("summary", ""),
                final_boxed_answer=ctx.get("final_boxed_answer", ""),
                error_message=ctx.get("error", ""),
            ),
        )
        message_history = ctx.get("message_history", [])
        llm_response = await self.llm_client.create_message(
            message_history=message_history
            + [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
        )

        return AgentContext(exceed_max_turn_summary=llm_response.response_text)
