# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""GAIA Common Verifier with exact match optimization."""

import re
import string
from typing import Any, Dict, List, Optional

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


class GAIACommonVerifier(BaseVerifier):
    """Verifier for GAIA benchmark using LLM-based evaluation with exact match optimization."""

    EVALUATION_PROMPT = """You are an evaluation assistant. Please determine if the predicted answer is equivalent to the labeled answer.

Question: {question}

Labeled Answer: {correct_answer}

Predicted Answer: {response}

Did the model give an answer **equivalent** to the labeled answer? Please respond with "Correct" if they are equivalent, or "Incorrect" if they are not equivalent. Do not include any other text.
"""

    @staticmethod
    def _normalize_number_str(number_str: str) -> float:
        """Normalize number string by removing units and commas."""
        for char in ["$", "%", ","]:
            number_str = number_str.replace(char, "")
        try:
            return float(number_str)
        except ValueError:
            return float("inf")

    @staticmethod
    def _normalize_str(input_str: str, remove_punct: bool = True) -> str:
        """Normalize string by removing whitespace, punctuation, and converting to lowercase."""
        no_spaces = re.sub(r"\s", "", input_str)
        if remove_punct:
            translator = str.maketrans("", "", string.punctuation)
            return no_spaces.lower().translate(translator)
        return no_spaces.lower()

    @staticmethod
    def _is_float(element: Any) -> bool:
        """Check if element can be converted to float."""
        try:
            float(element)
            return True
        except ValueError:
            return False

    @staticmethod
    def _split_string(s: str, char_list: List[str] = None) -> List[str]:
        """Split string by multiple delimiters."""
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)

    def _compare_as_number(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as numbers."""
        return self._normalize_number_str(model_answer) == float(ground_truth)

    def _compare_as_list(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as comma/semicolon-separated lists."""
        gt_elems = self._split_string(ground_truth)
        ma_elems = self._split_string(model_answer)

        if len(gt_elems) != len(ma_elems):
            return False

        comparisons = []
        for ma_elem, gt_elem in zip(ma_elems, gt_elems):
            if self._is_float(gt_elem):
                comparisons.append(
                    self._normalize_number_str(ma_elem) == float(gt_elem)
                )
            else:
                comparisons.append(
                    self._normalize_str(ma_elem, False)
                    == self._normalize_str(gt_elem, False)
                )

        return all(comparisons)

    def _compare_as_string(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as strings."""
        return self._normalize_str(model_answer) == self._normalize_str(ground_truth)

    def _exact_match(self, model_answer: str, ground_truth: str) -> bool:
        """Check if model answer exactly matches ground truth using GAIA-style normalization."""
        if model_answer is None:
            return False

        if self._is_float(ground_truth):
            return self._compare_as_number(model_answer, ground_truth)
        if any(char in ground_truth for char in [",", ";"]):
            return self._compare_as_list(model_answer, ground_truth)
        return self._compare_as_string(model_answer, ground_truth)

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
        """Verify answer using GAIA evaluation protocol with exact match optimization."""
        # First try exact match to avoid LLM calls
        if self._exact_match(predicted_answer, target):
            return EVAL_CORRECT

        prompt = self.EVALUATION_PROMPT.format(
            question=question, correct_answer=target, response=predicted_answer
        )

        response = await self.openai_client.chat.completions.create(
            model=LLM_GPT41,
            messages=[{"role": "user", "content": prompt}],
        )

        content = response.choices[0].message.content
        print(f"GAIA LLM Judge Response: {content}")

        content_normalized = content.strip().rstrip(".").lower()
        if content_normalized == "correct":
            return EVAL_CORRECT
        elif content_normalized == "incorrect":
            return EVAL_INCORRECT

        print(f"Warning: Could not parse GAIA judge response: {content}")
        return EVAL_NOT_ATTEMPTED
