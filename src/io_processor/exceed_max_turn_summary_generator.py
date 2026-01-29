# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Exceed Max Turn Summary Generator.

Generates summaries when task exceeds max turns without valid box.
"""

import re

from src.agents.context import AgentContext
from src.io_processor.base import BaseIOProcessor
from src.registry import ComponentType, register

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
        - <think>...</think> block (thinking content)
        - Main content after </think> and before <use_mcp_tool>
        - <use_mcp_tool>...</use_mcp_tool> block (tool call, ignored)

        Returns:
            - If content after </think> is non-empty, return that content
            - If content is empty, return think_content as fallback
            - Any <use_mcp_tool> block is always removed
        """
        if not text:
            return ""

        think_content = ""
        content = ""

        # Extract think content
        think_match = re.search(r"<think>([\s\S]*?)</think>", text)
        if think_match:
            think_content = think_match.group(1).strip()
            after_think = text[think_match.end() :]
        else:
            after_think = text

        # Remove <use_mcp_tool>...</use_mcp_tool> block from content
        mcp_match = re.search(r"<use_mcp_tool>[\s\S]*", after_think)
        if mcp_match:
            content = after_think[: mcp_match.start()].strip()
        else:
            content = after_think.strip()

        return content if content else think_content

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
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
        llm_response = await self.llm_client.create_message(
            message_history=message_history
        )

        # Post-process: prepend prefix to response and extract content
        if llm_response.response_text:
            full_text = FAILURE_SUMMARY_ASSISTANT_PREFIX + llm_response.response_text
            summary = self._extract_failure_experience_summary(full_text)
            return AgentContext(exceed_max_turn_summary=summary)

        return AgentContext(exceed_max_turn_summary=None)
