# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""HLE Verifier for benchmark evaluation."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_verifier import (
    EVAL_CORRECT,
    EVAL_INCORRECT,
    LLM_O3_MINI,
    RETRY_MAX_ATTEMPTS,
    RETRY_MULTIPLIER,
    BaseVerifier,
    get_eval_prompt,
)


class HLEVerifier(BaseVerifier):
    """Verifier for HLE and similar benchmarks using LLM-based evaluation."""

    MAX_TOKENS = 4096

    @property
    def JUDGE_PROMPT(self) -> str:
        return get_eval_prompt("hle", "judge_prompt")

    class ExtractedAnswer(BaseModel):
        model_config = {"strict": True}

        extracted_final_answer: str
        reasoning: str
        correct: Literal["yes", "no"]
        confidence: int

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
        """Verify answer using HLE-style LLM judge."""
        prompt = self.JUDGE_PROMPT.format(
            question=question, correct_answer=target, response=predicted_answer
        )

        response = await self.openai_client.beta.chat.completions.parse(
            model=LLM_O3_MINI,
            max_completion_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            response_format=self.ExtractedAnswer,
        )

        content = response.choices[0].message.parsed
        print(f"LLM as Judge Reasoning: {content.reasoning}")
        print(f"LLM as Judge Result: {content.correct}")
        print(f"LLM as Judge Confidence: {content.confidence}%")

        if content.correct == "yes":
            return EVAL_CORRECT
        if content.correct == "no":
            return EVAL_INCORRECT
        raise Exception(f"HLE LLM evaluation failed: {content}")
