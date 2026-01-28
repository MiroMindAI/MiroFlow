# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Failure Experience Summary Generator - generates failure summaries for retry logic.
"""

from src.agents.context import AgentContext
from src.io_processor.base import BaseIOProcessor
from src.registry import ComponentType, register


@register(ComponentType.IO_PROCESSOR, "FailureExperienceSummaryGenerator")
class FailureExperienceSummaryGenerator(BaseIOProcessor):
    """Generates failure experience summaries for pass@k retry logic."""

    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "prompt")

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        prompt = self.prompt_manager.render_prompt(
            "failure_summary_prompt",
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

        return AgentContext(failure_experience_summary=llm_response.response_text)
