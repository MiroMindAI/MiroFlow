# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""XBench Verifier for Chinese benchmark evaluation."""

import re
from typing import Any, Dict, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

from .base_verifier import (
    EVAL_CORRECT,
    EVAL_INCORRECT,
    EVAL_NOT_ATTEMPTED,
    LLM_GPT41,
    RETRY_MAX_ATTEMPTS,
    RETRY_MULTIPLIER,
    BaseVerifier,
)


class XBenchVerifier(BaseVerifier):
    """Verifier for XBench benchmark using LLM-based evaluation (Chinese).

    Aligned with MiroThinker's evaluation:
    - gpt-4.1-2025-04-14 as judge model
    - Free-text output with regex parsing (no Pydantic structured output)
    """

    # fmt: off
    JUDGE_PROMPT = """你是一个通用人工智能助手。根据下面给出的[正确答案], 判断以下对[原问题]的[回答]的回答是否正确。

[原问题]: {question}

[正确答案]: {correct_answer}

[回答]:{response}

你的判断必须按照以下格式和标准进行:

最终答案: 从[回答]中提取出的最终准确答案。如果[回答]中没有明确的最终答案, 则填写'无'。

解释: 根据[正确答案]解释为什么[最终答案]是正确的或错误的。只关注[最终答案]与[正确答案]之间是否存在实质性差异, 不要评论题目的背景, 不要尝试重新解题, 不要为任何不同于[正确答案]的答案辩护, 只专注于判断答案是否一致。

结论: 如果[最终答案]与上方给出的[正确答案]一致, 或者在数值题目中处于可接受的微小误差范围内, 则填写'正确'; 否则（即存在任何不一致、歧义、不等价或提取出的答案错误的情况）填写'错误'。"""
    # fmt: on

    @staticmethod
    def _parse_match_result(match):
        if match is None:
            return match
        match = match.group(0)
        try:
            target = match.split(":")[1].strip()
            return target
        except Exception:
            return match

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
        if predicted_answer is None:
            return EVAL_INCORRECT

        prompt = self.JUDGE_PROMPT.format(
            question=question, correct_answer=target, response=predicted_answer
        )

        response = await self.openai_client.chat.completions.create(
            model=LLM_GPT41,
            messages=[{"role": "user", "content": prompt}],
        )

        judge_response = response.choices[0].message.content
        if judge_response is None:
            return EVAL_NOT_ATTEMPTED

        # Extract grader conclusions using regex
        extract_match = re.search(r"最终答案:*(.*)", judge_response)
        extract_match = self._parse_match_result(extract_match)

        correct_match = re.search(r"结论:*\s*(正确|错误)", judge_response)
        correct_match = self._parse_match_result(correct_match)

        print(f"XBench Judge - Extract: {extract_match}, Correct: {correct_match}")

        if correct_match == "正确":
            return EVAL_CORRECT
        elif correct_match == "错误":
            return EVAL_INCORRECT

        print(
            f"Warning: Could not parse XBench judge response, correct_match={correct_match}"
        )
        return EVAL_NOT_ATTEMPTED
