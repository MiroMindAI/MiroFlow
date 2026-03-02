# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""FinSearchComp Verifier using dynamic LLM judge prompts."""

import re
from typing import Any, Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from .base_verifier import (
    EVAL_CORRECT,
    EVAL_INCORRECT,
    EVAL_NOT_ATTEMPTED,
    LLM_GPT4O_MINI,
    RETRY_MAX_ATTEMPTS,
    RETRY_MULTIPLIER,
    TEMP_DETERMINISTIC,
    BaseVerifier,
)


class FinSearchCompVerifier(BaseVerifier):
    """Verifier for FinSearchComp benchmark using dynamic LLM judge prompts."""

    MAX_TOKENS = 2048

    @retry(
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS),
    )
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Verify answer using FinSearchComp-style LLM judge with dynamic prompts."""
        if metadata is None:
            raise ValueError("FinSearchComp verifier requires metadata")

        judge_prompt_template = metadata["judge_prompt_template"]
        judge_system_prompt = metadata["judge_system_prompt"]
        response_reference = metadata.get("response_reference", "")
        ground_truth_finance = metadata.get("ground_truth_finance", "")

        formatted_prompt = judge_prompt_template.format(
            prompt=question,
            response_reference=response_reference,
            ground_truth=ground_truth_finance,
            response=predicted_answer,
        )

        messages = [
            {"role": "system", "content": judge_system_prompt},
            {"role": "user", "content": formatted_prompt},
        ]

        try:
            response = await self.openai_client.chat.completions.create(
                model=LLM_GPT4O_MINI,
                messages=messages,
                max_completion_tokens=self.MAX_TOKENS,
                temperature=TEMP_DETERMINISTIC,
            )

            content = response.choices[0].message.content
            print(f"FinSearchComp LLM Judge Response: {content}")
            return self._parse_response(content)
        except Exception as e:
            print(f"FinSearchComp LLM evaluation failed: {e}")
            return EVAL_NOT_ATTEMPTED

    @staticmethod
    def _parse_response(content: str) -> str:
        """Parse FinSearchComp judge response to extract evaluation result."""
        score_patterns = [
            (r'"answer_score":\s*1', EVAL_CORRECT),
            (r'"answer_score":\s*0', EVAL_INCORRECT),
            (r'"score":\s*1', EVAL_CORRECT),
            (r'"score":\s*0', EVAL_INCORRECT),
        ]

        for pattern, result in score_patterns:
            if re.search(pattern, content):
                return result

        print(f"Warning: Could not parse FinSearchComp judge response: {content}")
        return EVAL_NOT_ATTEMPTED
