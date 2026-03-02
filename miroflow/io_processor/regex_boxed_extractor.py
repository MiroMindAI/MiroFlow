# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Regex-based boxed answer extractor - aligned with MiroThinker.

This extractor uses pure regex to extract \\boxed{} content from the summary,
without calling LLM. It should be used when the summary already contains
the final answer in \\boxed{} format (e.g., when using summarize_prompt
that directly outputs \\boxed{}).
"""

from miroflow.agents.context import AgentContext
from miroflow.io_processor.base import BaseIOProcessor
from miroflow.registry import ComponentType, register


@register(ComponentType.IO_PROCESSOR, "RegexBoxedExtractor")
class RegexBoxedExtractor(BaseIOProcessor):
    """Pure regex-based boxed answer extractor, aligned with MiroThinker."""

    @staticmethod
    def _extract_boxed_content(text: str) -> str:
        """
        Extract content from \\boxed{} patterns in the text.

        Uses balanced brace counting to handle arbitrary levels of nested braces.
        Returns the last matched content, or empty string if no match found.
        """
        if not text:
            return ""

        matches = []
        i = 0

        while i < len(text):
            boxed_start = text.find(r"\boxed{", i)
            if boxed_start == -1:
                break

            content_start = boxed_start + 7  # len(r'\boxed{') = 7
            if content_start >= len(text):
                break

            brace_count = 1
            content_end = content_start

            while content_end < len(text) and brace_count > 0:
                char = text[content_end]
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                content_end += 1

            if brace_count == 0:
                content = text[content_start : content_end - 1]
                matches.append(content)
                i = content_end
            else:
                i = content_start

        return matches[-1] if matches else ""

    @staticmethod
    def _extract_boxed_from_message_history(message_history: list) -> str:
        """Extract the last \\boxed{} content from message_history as fallback.

        Scans all assistant messages in reverse order to find intermediate
        boxed answers produced during the agent's execution.
        """
        if not message_history:
            return ""

        for msg in reversed(message_history):
            if msg.get("role") != "assistant":
                continue
            content = msg.get("content", "")
            if isinstance(content, list):
                content = " ".join(
                    item.get("text", "") for item in content if isinstance(item, dict)
                )
            if not isinstance(content, str):
                continue
            boxed = RegexBoxedExtractor._extract_boxed_content(content)
            if boxed:
                return boxed
        return ""

    async def run_internal(self, ctx: AgentContext) -> AgentContext:
        summary = ctx.get("summary", "")
        boxed_content = self._extract_boxed_content(summary)

        if boxed_content:
            final_boxed_answer = boxed_content
        else:
            # Final retry fallback: scan message_history for intermediate boxed answers
            is_final_retry = ctx.get("is_final_retry", False)
            if is_final_retry:
                message_history = ctx.get("message_history", [])
                fallback = self._extract_boxed_from_message_history(message_history)
                if fallback:
                    final_boxed_answer = fallback
                else:
                    final_boxed_answer = "No \\boxed{} content found."
            else:
                final_boxed_answer = "No \\boxed{} content found."

        return AgentContext(final_boxed_answer=final_boxed_answer)
