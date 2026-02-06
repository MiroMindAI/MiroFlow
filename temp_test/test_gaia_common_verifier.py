"""
Temp test for GAIACommonVerifier - testing exact match + LLM judge.
Run: cd <project_root> && python -m temp_test.test_gaia_common_verifier
"""

import asyncio
import os
import sys
import types

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv  # noqa: E402

load_dotenv()


# ============================================================================
# Isolated import: avoid the full src.benchmark import chain (needs mcp, etc.)
# We create a fake package so that relative imports inside the verifiers work.
# ============================================================================


def _import_verifiers():
    """Import verifier modules without triggering the full src.benchmark chain."""
    import importlib.util

    verifiers_dir = os.path.join(PROJECT_ROOT, "src", "benchmark", "verifiers")

    # Create fake parent packages so relative imports resolve
    for pkg_name in ["src", "src.benchmark", "src.benchmark.verifiers"]:
        if pkg_name not in sys.modules:
            mod = types.ModuleType(pkg_name)
            mod.__path__ = []
            mod.__package__ = pkg_name
            sys.modules[pkg_name] = mod

    # Load base_verifier
    spec_base = importlib.util.spec_from_file_location(
        "src.benchmark.verifiers.base_verifier",
        os.path.join(verifiers_dir, "base_verifier.py"),
        submodule_search_locations=[],
    )
    base_mod = importlib.util.module_from_spec(spec_base)
    base_mod.__package__ = "src.benchmark.verifiers"
    sys.modules["src.benchmark.verifiers.base_verifier"] = base_mod
    spec_base.loader.exec_module(base_mod)

    # Load gaia_common_verifier
    spec_gaia = importlib.util.spec_from_file_location(
        "src.benchmark.verifiers.gaia_common_verifier",
        os.path.join(verifiers_dir, "gaia_common_verifier.py"),
        submodule_search_locations=[],
    )
    gaia_mod = importlib.util.module_from_spec(spec_gaia)
    gaia_mod.__package__ = "src.benchmark.verifiers"
    sys.modules["src.benchmark.verifiers.gaia_common_verifier"] = gaia_mod
    spec_gaia.loader.exec_module(gaia_mod)

    return base_mod, gaia_mod


base_verifier, gaia_common_verifier = _import_verifiers()

GAIACommonVerifier = gaia_common_verifier.GAIACommonVerifier
EVAL_CORRECT = base_verifier.EVAL_CORRECT
EVAL_INCORRECT = base_verifier.EVAL_INCORRECT
EVAL_NOT_ATTEMPTED = base_verifier.EVAL_NOT_ATTEMPTED


# ============================================================================
# Part 1: Test exact match (no LLM needed)
# ============================================================================


def test_exact_match():
    """Test the exact match logic without needing an OpenAI client."""
    v = GAIACommonVerifier(openai_client=None)

    print("=" * 60)
    print("PART 1: Testing exact match (no LLM)")
    print("=" * 60)

    passed = 0
    failed = 0

    def check(predicted, target, expected, label=""):
        nonlocal passed, failed
        result = v._exact_match(predicted, target)
        status = "PASS" if result == expected else "FAIL"
        if status == "PASS":
            passed += 1
        else:
            failed += 1
        extra = f" ({label})" if label else ""
        print(
            f"  [{status}] _exact_match('{predicted}', '{target}') = {result} (expected {expected}){extra}"
        )

    # --- Number comparisons ---
    print("\n--- Number comparisons ---")
    check("42", "42", True, "identical int")
    check("42.0", "42", True, "float vs int")
    check("$1,234", "1234", True, "currency format")
    check("$1,234.56", "1234.56", True, "currency with decimals")
    check("50%", "50", True, "percentage")
    check("99", "100", False, "different numbers")
    check("abc", "42", False, "non-numeric predicted")

    # --- String comparisons ---
    print("\n--- String comparisons ---")
    check("Hello World", "hello world", True, "case insensitive")
    check("Hello, World!", "hello world", True, "punctuation removed")
    check("  spaced  ", "spaced", True, "whitespace removed")
    check("different", "answer", False, "completely different")
    check("Paris", "paris", True, "simple case")
    check("New York City", "newyorkcity", True, "spaces removed")

    # --- List comparisons ---
    print("\n--- List comparisons ---")
    check("a, b, c", "a, b, c", True, "identical list")
    check("a,b,c", "a, b, c", True, "no spaces in predicted")
    check("a; b; c", "a; b; c", True, "semicolon-separated")
    check("1, 2, 3", "1, 2, 3", True, "numeric list")
    check("a, b", "a, b, c", False, "different length")
    check("a, c, b", "a, b, c", False, "different order")

    # --- None handling ---
    print("\n--- None handling ---")
    check(None, "anything", False, "None predicted")

    print(f"\n  Summary: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================================
# Part 2: Test inlined EVALUATION_PROMPT
# ============================================================================


def test_prompt_loading():
    """Test that the inlined EVALUATION_PROMPT is accessible and well-formed."""
    print("\n" + "=" * 60)
    print("PART 2: Testing inlined EVALUATION_PROMPT")
    print("=" * 60)

    ok = True

    try:
        v = GAIACommonVerifier(openai_client=None)
        prompt = v.EVALUATION_PROMPT
        print(
            f"  [PASS] GAIACommonVerifier.EVALUATION_PROMPT accessible ({len(prompt)} chars)"
        )

        # Verify the prompt has the expected placeholders
        count = prompt.count("{}")
        if count == 3:
            print(
                f"  [PASS] Prompt has {count} placeholders for .format(question, target, predicted)"
            )
        else:
            print(f"  [FAIL] Prompt has {count} placeholder(s), expected 3")
            ok = False

        # Verify it can be formatted
        formatted = prompt.format("test question", "test target", "test answer")
        if (
            "test question" in formatted
            and "test target" in formatted
            and "test answer" in formatted
        ):
            print("  [PASS] Prompt .format() works correctly")
        else:
            print("  [FAIL] Prompt .format() did not substitute placeholders")
            ok = False
    except Exception as e:
        print(f"  [FAIL] {type(e).__name__}: {e}")
        ok = False

    return ok


# ============================================================================
# Part 3: Test LLM-based verification (needs OpenAI client)
# ============================================================================


async def test_llm_verify():
    """Test the full LLM-based verify method."""
    print("\n" + "=" * 60)
    print("PART 3: Testing LLM-based verification (calls gpt-4o-mini)")
    print("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key:
        print("  [SKIP] OPENAI_API_KEY not set, skipping LLM tests")
        return True

    print(f"  Using base_url: {base_url}")
    print(f"  Using api_key: {api_key[:8]}...")

    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    v = GAIACommonVerifier(openai_client=client)

    # Test cases designed to NOT exact-match, forcing LLM evaluation
    test_cases = [
        {
            "question": "What are the names of Barack Obama's children?",
            "target": "Malia and Sasha",
            "predicted": "sasha and malia obama",
            "expected": "CORRECT",
            "note": "semantically correct, different order/format",
        },
        {
            "question": "What is the capital of France?",
            "target": "Paris",
            "predicted": "The capital city of France is Paris.",
            "expected": "CORRECT",
            "note": "correct with extra surrounding text",
        },
        {
            "question": "What is 2+2?",
            "target": "4",
            "predicted": "The answer is 5",
            "expected": "INCORRECT",
            "note": "wrong answer",
        },
        {
            "question": "Who wrote Romeo and Juliet?",
            "target": "William Shakespeare",
            "predicted": "I don't know",
            "expected": "NOT_ATTEMPTED",
            "note": "not attempted",
        },
    ]

    passed = 0
    failed = 0

    for i, tc in enumerate(test_cases):
        try:
            result = await v.verify(
                question=tc["question"],
                target=tc["target"],
                predicted_answer=tc["predicted"],
            )
            status = "PASS" if result == tc["expected"] else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1
            print(
                f"  [{status}] Case {i + 1} ({tc['note']}): got '{result}', expected '{tc['expected']}'"
            )
        except Exception as e:
            failed += 1
            print(f"  [FAIL] Case {i + 1} ({tc['note']}): {type(e).__name__}: {e}")

    print(f"\n  Summary: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================================
# Part 4: verify() with exact match cases (no LLM call needed)
# ============================================================================


async def test_exact_match_via_verify():
    """Test that verify() returns CORRECT immediately for exact matches (no LLM call)."""
    print("\n" + "=" * 60)
    print("PART 4: Testing verify() with exact match cases (no LLM call)")
    print("=" * 60)

    # No OpenAI client - will error if LLM is accidentally called
    v = GAIACommonVerifier(openai_client=None)

    cases = [
        ("What is 2+2?", "4", "4", "identical number"),
        ("What city?", "Paris", "paris", "case difference"),
        ("How much?", "1234", "$1,234", "currency format"),
    ]

    passed = 0
    failed = 0

    for question, target, predicted, label in cases:
        try:
            result = await v.verify(question, target, predicted)
            status = "PASS" if result == EVAL_CORRECT else "FAIL"
            if status == "PASS":
                passed += 1
            else:
                failed += 1
            print(
                f"  [{status}] verify('{predicted}' vs '{target}') = {result} ({label})"
            )
        except Exception as e:
            failed += 1
            print(
                f"  [FAIL] verify('{predicted}' vs '{target}'): {type(e).__name__}: {e} ({label})"
            )

    print(f"\n  Summary: {passed} passed, {failed} failed")
    return failed == 0


# ============================================================================
# Main
# ============================================================================


def main():
    print("\n" + "=" * 60)
    print("  GAIACommonVerifier Test Suite")
    print("=" * 60)

    results = {}

    # Part 1: Exact match tests
    results["exact_match"] = test_exact_match()

    # Part 2: Prompt loading
    results["prompt_loading"] = test_prompt_loading()

    # Part 3: LLM-based tests
    results["llm_verify"] = asyncio.run(test_llm_verify())

    # Part 4: verify() with exact match (no LLM)
    results["verify_exact"] = asyncio.run(test_exact_match_via_verify())

    # Final summary
    print("\n" + "=" * 60)
    print("  FINAL SUMMARY")
    print("=" * 60)
    for name, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'} - {name}")
    print("=" * 60)

    all_passed = all(results.values())
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
