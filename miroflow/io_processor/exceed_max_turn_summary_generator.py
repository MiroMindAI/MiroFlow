# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Exceed Max Turn Summary Generator.

Generates summaries when task exceeds max turns without valid box.
"""

import re

from miroflow.agents.context import AgentContext
from miroflow.io_processor.base import BaseIOProcessor
from miroflow.registry import ComponentType, register
from miroflow.benchmark.eval_utils import is_valid_box
from miroflow.llm.base import ContextLimitError

# Assistant prefix for failure summary generation (aligned with MiroThinker)
# This guides the model to think first and then output structured content
# fmt: off
FAILURE_SUMMARY_THINK_CONTENT = """We need to write a structured post-mortem style summary **without calling any tools**, explaining why the task was not completed, using these required sections:

* **Failure type**: pick one from **incomplete / blocked / misdirected / format_missed**
* **What happened**: describe the approach taken and why it didn't reach a final answer
* **Useful findings**: list any facts, intermediate results, or conclusions that can be reused"""
# fmt: on

FAILURE_SUMMARY_ASSISTANT_PREFIX = (
    f"<think>\n{FAILURE_SUMMARY_THINK_CONTENT}\n</think>\n\n"
)


@register(ComponentType.IO_PROCESSOR, "ExceedMaxTurnSummaryGenerator")
class ExceedMaxTurnSummaryGenerator(BaseIOProcessor):
    """Generates summaries for retry logic when task exceeds max turns without valid box.

    Uses assistant prefill mechanism aligned with MiroThinker to ensure structured output.
    """

    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "prompt")

    @staticmethod
    def _extract_failure_experience_summary(text: str) -> str:
        """Extract failure experience summary from LLM response text.

        The text may contain:
        - Multiple <think>...</think> blocks (all removed from final output)
        - Main content after removing all think blocks
        - <use_mcp_tool>...</use_mcp_tool> block (tool call, ignored)
        - Empty \\boxed{} patterns (ignored)

        Returns:
            - Content with all <think> blocks removed
            - If content is empty after filtering, return last think_content as fallback
            - Any <use_mcp_tool> block is always removed
        """
        if not text:
            return ""

        # Extract all think contents (for fallback)
        think_matches = list(re.finditer(r"<think>([\s\S]*?)</think>", text))
        last_think_content = ""
        if think_matches:
            last_think_content = think_matches[-1].group(1).strip()

        # Remove ALL <think>...</think> blocks from content
        content = re.sub(r"<think>[\s\S]*?</think>", "", text).strip()

        # Remove <use_mcp_tool>...</use_mcp_tool> block from content
        content = re.sub(r"<use_mcp_tool>[\s\S]*", "", content).strip()

        # Remove empty \boxed{} patterns (common pollution in model output)
        content = re.sub(r"\\boxed\{\s*\}", "", content).strip()

        return content if content else last_think_content

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        final_boxed_answer = ctx.get("final_boxed_answer", "")
        if is_valid_box(final_boxed_answer):
            return AgentContext(exceed_max_turn_summary=None)

        # Render the simplified prompt (no variables needed, context is in message_history)
        prompt = self.prompt_manager.render_prompt(
            "exceed_max_turn_summary_prompt", context={}
        )

        # Build message history for failure summary generation
        message_history = ctx.get("message_history", []).copy()

        # If last message is from user, remove it (aligned with MiroThinker)
        if message_history and message_history[-1].get("role") == "user":
            message_history.pop()

        # Append user prompt
        message_history.append(
            {"role": "user", "content": [{"type": "text", "text": prompt}]}
        )

        # Append assistant prefix (prefill mechanism - key for structured output)
        message_history.append(
            {"role": "assistant", "content": FAILURE_SUMMARY_ASSISTANT_PREFIX}
        )

        # Call LLM - it will continue from the assistant prefix
        try:
            llm_response = await self.llm_client.create_message(
                message_history=message_history
            )
        except ContextLimitError:
            return AgentContext(
                exceed_max_turn_summary="Task interrupted due to context limit."
            )

        # Post-process: prepend prefix to response and extract content
        if llm_response.response_text:
            full_text = FAILURE_SUMMARY_ASSISTANT_PREFIX + llm_response.response_text
            summary = self._extract_failure_experience_summary(full_text)
            return AgentContext(exceed_max_turn_summary=summary)

        return AgentContext(exceed_max_turn_summary=None)
