# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Base verifier class and shared constants for benchmark evaluation."""

from typing import Any, Dict, Optional

from openai import AsyncOpenAI

# ============================================================================
# Evaluation Constants
# ============================================================================

EVAL_CORRECT = "CORRECT"
EVAL_INCORRECT = "INCORRECT"
EVAL_NOT_ATTEMPTED = "NOT_ATTEMPTED"
EVAL_ERROR = "ERROR"

LLM_GPT4O_MINI = "gpt-4o-mini"
LLM_GPT41 = "gpt-4.1-2025-04-14"
LLM_O3_MINI = "o3-mini-2025-01-31"
LLM_O3 = "o3"

TEMP_DETERMINISTIC = 0.0
RETRY_MULTIPLIER = 5
RETRY_MAX_ATTEMPTS = 5


# ============================================================================
# Base Verifier Class
# ============================================================================


class BaseVerifier:
    """Base class for benchmark answer verifiers."""

    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        self.openai_client = openai_client

    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Verify if predicted answer matches target. Returns: CORRECT, INCORRECT, or NOT_ATTEMPTED."""
        raise NotImplementedError("Subclasses must implement verify()")
