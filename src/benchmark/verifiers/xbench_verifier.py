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
)


class XBenchVerifier(BaseVerifier):
    """Verifier for XBench benchmark using LLM-based evaluation (Chinese)."""

    MAX_TOKENS = 4096

    JUDGE_PROMPT = """你是一个通用人工智能助手。根据下面给出的[正确答案], 判断以下对[原问题]的[回答]的回答是否正确。

[原问题]: {question}

[正确答案]: {correct_answer}

[回答]:{response}

你的判断必须按照以下格式和标准进行:

最终答案: 从[回答]中提取出的最终准确答案。如果[回答]中没有明确的最终答案, 则填写'无'。

解释: 根据[原问题]解释为什么[最终答案]是正确的或错误的。只关注[最终答案]与[正确答案]之间是否存在实质性差异, 不要评论题目的背景, 不要尝试重新解题, 不要为任何不同于[正确答案]的答案辩护, 只专注于判断答案是否一致。

结论: 如果[最终答案]与上方给出的[正确答案]一致, 或者在数值题目中处于可接受的微小误差范围内, 则填写'正确'; 否则（即存在任何不一致、歧义、不等价或提取出的答案错误的情况）填写'错误'。"""

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
