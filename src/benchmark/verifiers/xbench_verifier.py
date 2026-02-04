# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""XBench Verifier for Chinese benchmark evaluation."""

from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from .base_verifier import (
    EVAL_CORRECT,
    EVAL_INCORRECT,
    LLM_O3,
    RETRY_MAX_ATTEMPTS,
    RETRY_MULTIPLIER,
    BaseVerifier,
    get_eval_prompt,
)


class XBenchVerifier(BaseVerifier):
    """Verifier for XBench benchmark using LLM-based evaluation (Chinese)."""

    MAX_TOKENS = 4096

    @property
    def JUDGE_PROMPT(self) -> str:
        return get_eval_prompt("xbench", "judge_prompt")

    class ExtractedAnswer(BaseModel):
        model_config = {"strict": True}

        最终答案: str
        解释: str
        结论: Literal["正确", "错误"]

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
        """Verify answer using XBench-style LLM judge (Chinese evaluation)."""
        prompt = self.JUDGE_PROMPT.format(
            question=question, correct_answer=target, response=predicted_answer
        )

        response = await self.openai_client.beta.chat.completions.parse(
            model=LLM_O3,
            max_completion_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            response_format=self.ExtractedAnswer,
        )

        content = response.choices[0].message.parsed
        print(f"XBench LLM Judge Extracted Answer: {content.最终答案}")
        print(f"XBench LLM Judge Reasoning: {content.解释}")
        print(f"XBench LLM Judge Result: {content.结论}")

        if content.结论 == "正确":
            return EVAL_CORRECT
        if content.结论 == "错误":
            return EVAL_INCORRECT
        raise Exception(f"XBench LLM evaluation failed: {content}")
