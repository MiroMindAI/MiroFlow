# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""GAIA Verifier using exact matching with normalization."""

import re
import string
import warnings
from typing import Any, Dict, List, Optional

from .base_verifier import EVAL_CORRECT, EVAL_INCORRECT, BaseVerifier


class GAIAVerifier(BaseVerifier):
    """Verifier for GAIA benchmark using exact matching with normalization."""

    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Verify answer using GAIA-style exact matching with normalization."""
        try:
            is_correct = self._score_answer(predicted_answer, target)
            return EVAL_CORRECT if is_correct else EVAL_INCORRECT
        except Exception as e:
            print(f"GAIA evaluation failed: {e}")
            raise e

    @staticmethod
    def _normalize_number_str(number_str: str) -> float:
        """Normalize number string by removing units and commas."""
        for char in ["$", "%", ","]:
            number_str = number_str.replace(char, "")
        try:
            return float(number_str)
        except ValueError:
            print(f"String {number_str} cannot be normalized to number.")
            return float("inf")

    @staticmethod
    def _split_string(s: str, char_list: List[str] = None) -> List[str]:
        """Split string by multiple delimiters."""
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)

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

    def _compare_as_number(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as numbers."""
        print(f"Evaluating {model_answer} as a number.")
        return self._normalize_number_str(model_answer) == float(ground_truth)

    def _compare_as_list(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as comma/semicolon-separated lists."""
        print(f"Evaluating {model_answer} as a list.")

        gt_elems = self._split_string(ground_truth)
        ma_elems = self._split_string(model_answer)

        if len(gt_elems) != len(ma_elems):
            warnings.warn("Answer lists have different lengths.", UserWarning)
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
        print(f"Evaluating {model_answer} as a string.")
        return self._normalize_str(model_answer) == self._normalize_str(ground_truth)

    def _score_answer(self, model_answer: str, ground_truth: str) -> bool:
        """Score model answer against ground truth using GAIA evaluation logic."""
        if model_answer is None:
            model_answer = "None"

        if self._is_float(ground_truth):
            return self._compare_as_number(model_answer, ground_truth)
        if any(char in ground_truth for char in [",", ";"]):
            return self._compare_as_list(model_answer, ground_truth)
        return self._compare_as_string(model_answer, ground_truth)
