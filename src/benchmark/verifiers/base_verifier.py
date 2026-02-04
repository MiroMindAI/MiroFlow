# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Base verifier class and shared constants for benchmark evaluation."""

from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from openai import AsyncOpenAI

# ============================================================================
# Evaluation Constants
# ============================================================================

EVAL_CORRECT = "CORRECT"
EVAL_INCORRECT = "INCORRECT"
EVAL_NOT_ATTEMPTED = "NOT_ATTEMPTED"
EVAL_ERROR = "ERROR"

LLM_GPT4O_MINI = "gpt-4o-mini"
LLM_O3_MINI = "o3-mini-2025-01-31"
LLM_O3 = "o3"

TEMP_DETERMINISTIC = 0.0
RETRY_MULTIPLIER = 5
RETRY_MAX_ATTEMPTS = 5


# ============================================================================
# Prompt Loading
# ============================================================================

_PROMPTS_CACHE: Optional[Dict[str, Any]] = None


def _load_eval_prompts() -> Dict[str, Any]:
    """Load evaluation prompts from YAML file."""
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE

    prompts_file = Path(__file__).parent.parent / "eval_prompts.yaml"
    if not prompts_file.exists():
        raise FileNotFoundError(f"Evaluation prompts file not found: {prompts_file}")

    with open(prompts_file, "r", encoding="utf-8") as f:
        _PROMPTS_CACHE = yaml.safe_load(f)

    return _PROMPTS_CACHE


def get_eval_prompt(verifier_name: str, prompt_key: str) -> str:
    """Get a specific evaluation prompt from the YAML file."""
    prompts = _load_eval_prompts()
    if verifier_name not in prompts:
        raise KeyError(f"Verifier '{verifier_name}' not found")
    if prompt_key not in prompts[verifier_name]:
        raise KeyError(f"Prompt key '{prompt_key}' not found for '{verifier_name}'")
    return prompts[verifier_name][prompt_key].strip()


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
