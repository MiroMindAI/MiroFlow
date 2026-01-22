# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Evaluation utilities for benchmark tasks with JSONL-based infrastructure."""

import json
import os
import re
import string
import subprocess
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Union

import yaml
from omegaconf import DictConfig
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

# Type aliases
EvaluationResult = str
TaskParser = Callable[[str], "Task"]


# ============================================================================
# Status Constants
# ============================================================================

STATUS_PENDING = "pending"
STATUS_FAILED = "failed"
STATUS_COMPLETED = "completed"
STATUS_RESULT_JUDGED = "result_judged"


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class Task:
    """Benchmark task definition with inputs and expected outputs."""
    
    task_id: str
    task_question: str
    file_path: Optional[Union[str, List[str]]] = None
    ground_truth: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class AttemptResult:
    """Single attempt result for a benchmark task."""
    
    def __init__(
        self,
        task: Task,
        attempt_id: int,
        model_response: str = "",
        model_boxed_answer: str = "",
        status: str = STATUS_PENDING,
        log_path: Optional[Path] = None,
        judge_result: Optional[str] = None,
        is_correct: bool = False,
        error_message: Optional[str] = None,
    ):
        self.task = task
        self.attempt_id = attempt_id
        self.model_response = model_response
        self.model_boxed_answer = model_boxed_answer
        self.status = status
        self.log_path = log_path
        self.judge_result = judge_result
        self.is_correct = is_correct
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task.task_id,
            "attempt_id": self.attempt_id,
            "model_response": self.model_response,
            "model_boxed_answer": self.model_boxed_answer,
            "status": self.status,
            "log_path": str(self.log_path) if self.log_path else None,
            "judge_result": self.judge_result,
            "is_correct": self.is_correct,
            "error_message": self.error_message,
        }
    
    def update_from_response(self, response: Dict[str, Any], log_path: Path):
        """Update with response data from agent.run()."""
        self.model_response = response
        self.model_boxed_answer = response.get('final_boxed_answer', '')
        self.status = STATUS_COMPLETED if self.model_boxed_answer else STATUS_FAILED
        self.log_path = log_path
    
    async def update_with_evaluation(self, evaluation_result: str):
        """Update with evaluation result and log file."""
        self.judge_result = evaluation_result
        self.is_correct = evaluation_result == "CORRECT"
        if self.log_path:
            await self.update_log_with_evaluation(evaluation_result)
    
    async def update_log_with_evaluation(self, evaluation_result: str):
        """Update log file with evaluation result."""
        if not self.log_path:
            return
        
        try:
            log_file = Path(self.log_path)
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)

            if "task_meta" not in log_data:
                log_data["task_meta"] = {}
            log_data["task_meta"]["judge_result"] = evaluation_result

            temp_log_file = log_file.with_suffix(f"{log_file.suffix}.tmp")
            with open(temp_log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

            os.replace(temp_log_file, log_file)
            print(f"    Updated log file {log_file.name} with evaluation result.")
        except Exception as e:
            print(f"    Error updating log file {self.log_path}: {e}")


class TaskResult:
    """Evaluation result with attempts and pass@k metrics."""

    def __init__(self, task: Task):
        self.task = task
        self.model_response = ""
        self.model_boxed_answer = ""
        self.status = STATUS_PENDING
        self.error_message = ""
        self.judge_result = None
        self.log_path = None
        self.attempts = []
        self.pass_at_k_success = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to serializable dictionary."""
        result = self.__dict__.copy()

        # Flatten task object
        if "task" in result:
            task = result.pop("task")
            result["task_id"] = task.task_id
            result["task_question"] = task.task_question
            result["ground_truth"] = task.ground_truth
            result["file_path"] = task.file_path
            result["metadata"] = task.metadata.copy() if task.metadata else {}

        # Convert Path objects to strings
        for field in ["log_path", "file_path"]:
            if isinstance(result.get(field), Path):
                result[field] = str(result[field])

        # Convert AttemptResult objects to dicts
        for i, attempt in enumerate(result.get("attempts", [])):
            if isinstance(attempt, AttemptResult):
                result["attempts"][i] = attempt.to_dict()
            elif isinstance(attempt, dict) and isinstance(attempt.get("log_path"), Path):
                attempt["log_path"] = str(attempt["log_path"])

        return result

    def update_with_attempt(self, attempt_result: AttemptResult):
        """Update with attempt result."""
        self.attempts.append(attempt_result)
        attempt_num = len(self.attempts)
        
        # Update main result with first or successful attempt
        if attempt_num == 1 or (not self.model_boxed_answer and attempt_result.status == STATUS_COMPLETED):
            self.model_response = attempt_result.model_response
            self.model_boxed_answer = attempt_result.model_boxed_answer
            self.log_path = attempt_result.log_path
            self.status = attempt_result.status
            self.error_message = attempt_result.error_message


# ============================================================================
# Benchmark Evaluators
# ============================================================================

class Evaluator:
    """Generic benchmark evaluator for JSONL-based datasets with pass@k support."""

    def __init__(self, cfg: DictConfig, parse_func: Optional[TaskParser] = None):
        self.cfg = cfg
        self.data_dir = Path(cfg.data.data_dir)
        self.benchmark_name = cfg.name
        self.pass_at_k = cfg.execution.get("pass_at_k", 1)
        self.evaluation_llm = AsyncOpenAI(api_key=cfg.openai_api_key)
        self.tasks: List[Task] = []
        
        metadata_file = cfg.data.get("metadata_file")
        self.metadata_file = self.data_dir / metadata_file if metadata_file else None
        self.parse_func = parse_func

    def load_tasks(self) -> List[Task]:
        """Load benchmark tasks from JSONL metadata file."""
        self._validate_load_requirements()
        print(f"Loading tasks from {self.metadata_file}")
        
        tasks = self._parse_tasks_from_file()
        tasks = self._apply_task_limit(tasks)
        
        self.tasks = tasks
        print(f"Loaded {len(tasks)} tasks")
        return tasks

    def _validate_load_requirements(self) -> None:
        """Validate required components for loading tasks."""
        if not self.metadata_file:
            raise ValueError("metadata_file must be provided")
        
        # Auto-download gaia-val if needed
        if "gaia" in self.benchmark_name.lower() and not self.metadata_file.exists():
            self._download_gaia_val()
        
        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_file}")
        if not self.parse_func:
            raise ValueError("parse_func must be provided")

    def _download_gaia_val(self) -> None:
        """Download and extract gaia-val dataset if it doesn't exist."""        
        gaia_val_dir = self.data_dir

        if (gaia_val_dir / "standardized_data.jsonl").exists():
            return
        
        # Determine which dataset to download based on benchmark name
        is_text_only = "text-only" in self.benchmark_name.lower()
        if is_text_only:
            dataset_name = "gaia-val-text-only"
            zip_filename = "gaia-val-text-only.zip"
        else:
            dataset_name = "gaia-val"
            zip_filename = "gaia-val.zip"
        
        print(f"Downloading {dataset_name} from HuggingFace...")
        zip_file = self.data_dir.parent / zip_filename
        
        try:
            # Download
            download_url = f"https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/{zip_filename}"
            subprocess.run(
                ["wget", "--no-check-certificate", "-O", str(zip_file), download_url],
                check=True, capture_output=True, text=True
            )
            
            # Extract to parent directory (zip contains dataset folder)
            # This ensures final structure is data/{dataset_name}/, not data/{dataset_name}/{dataset_name}/
            subprocess.run(
                ["unzip", "-P", "pf4*", "-d", str(self.data_dir.parent), str(zip_file)],
                check=True, capture_output=True, text=True
            )
            
            print(f"Successfully extracted {dataset_name} to {gaia_val_dir}")
            
        except Exception as e:
            print(f"Failed to download {dataset_name}: {e}")
            raise
        finally:
            # Cleanup
            if zip_file.exists():
                zip_file.unlink()

    def _should_include_task(self, task: Task) -> bool:
        """Check if task should be included based on whitelist."""
        whitelist = self.cfg.data.get("whitelist", [])
        return task.task_id in whitelist if whitelist else True

    def _parse_tasks_from_file(self) -> List[Task]:
        """Parse tasks from JSONL file with whitelist filter."""
        tasks = []
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                try:
                    task = self.parse_func(line.strip())
                    if self._should_include_task(task):
                        tasks.append(task)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {i}: {e}")
        return tasks

    def _apply_task_limit(self, tasks: List[Task]) -> List[Task]:
        """Apply max_tasks limit."""
        max_tasks = self.cfg.execution.max_tasks
        # If max_tasks is None, -1, or any negative number, return all tasks
        if max_tasks is None or max_tasks < 0:
            return tasks
        return tasks[:max_tasks]

    def save_results(self, results: List["TaskResult"], output_path: Path) -> Path:
        """Save evaluation results to JSONL file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            for result in results:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")
        print(f"Results saved to {output_path}")
        return output_path

    async def evaluate_accuracy(self, results: List["TaskResult"]) -> float:
        """Evaluate pass@k accuracy across all results."""
        if not results:
            print("No results to evaluate")
            return 0.0

        print(f"Calculating pass@{self.pass_at_k} accuracy for {len(results)} results...")

        correct_count = sum(1 for result in results if result.pass_at_k_success)
        total_count = len(results)

        for result in results:
            self._print_task_result(result)

        accuracy = correct_count / total_count if total_count > 0 else 0.0
        self._print_accuracy_summary(correct_count, total_count, accuracy)
        return accuracy

    def _print_task_result(self, result: TaskResult) -> None:
        """Print detailed results for a task."""
        status = "✅ SUCCESS" if result.pass_at_k_success else "❌ FAILED"
        print(f"\nTask {result.task.task_id}:")
        print(f"  Attempts: {len(result.attempts)}")
        print(f"  Pass@{self.pass_at_k}: {status}")

        for attempt in result.attempts:
            self._print_attempt_details(attempt)

        print("  " + "=" * 50)
        print(f"  Reference: {result.task.ground_truth}")
        print("  " + "=" * 50)

    def _print_attempt_details(self, attempt: AttemptResult) -> None:
        """Print details of an attempt."""
        judge_result = attempt.judge_result or "NOT_VERIFIED"
        icon = self._get_status_icon(attempt.is_correct, judge_result)
        print(f"    Attempt {attempt.attempt_id}: {icon} {judge_result}")
        if attempt.model_boxed_answer:
            print(f"      Answer: {attempt.model_boxed_answer}")

    @staticmethod
    def _get_status_icon(is_correct: bool, judge_result: str) -> str:
        """Get status icon for attempt."""
        if is_correct:
            return "✅"
        return "❌" if judge_result != "NOT_VERIFIED" else "⚠️"

    def _print_accuracy_summary(self, correct_count: int, total_count: int, accuracy: float) -> None:
        """Print accuracy summary."""
        print(f"\nPass@{self.pass_at_k} Final Results:")
        print(f"Tasks passed: {correct_count}/{total_count}")
        print(f"Pass@{self.pass_at_k} Accuracy: {accuracy:.2%}")

    async def verify_attempt_result(
        self,
        task: Task,
        attempt: int,
        attempt_result: AttemptResult,
    ) -> AttemptResult:
        """Verify a single attempt result using LLM judge."""
        if attempt_result.status != STATUS_COMPLETED:
            print(f"    ⚠️  Attempt {attempt}: No valid answer to verify")
            return attempt_result
        
        if attempt_result.judge_result is None:
            print(f"    Verifying answer for attempt {attempt}...")
            try:
                evaluation_result = await verify_answer_for_benchmark(
                    openai_client=self.evaluation_llm,
                    benchmark_name=self.benchmark_name,
                    question=task.task_question,
                    target=task.ground_truth,
                    predicted_answer=attempt_result.model_boxed_answer,
                    metadata=task.metadata,
                )
            except Exception as e:
                print(f"    Error verifying attempt {attempt}: {e}")
                evaluation_result = EVAL_ERROR
            
            await attempt_result.update_with_evaluation(evaluation_result)
        
        status = "✅ CORRECT" if attempt_result.is_correct else f"❌ INCORRECT ({attempt_result.judge_result})"
        print(f"    {status}")
        return attempt_result


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
    
    prompts_file = Path(__file__).parent / "eval_prompts.yaml"
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


# ============================================================================
# Verifier Factory and Router
# ============================================================================

def get_verifier(benchmark_name: str, openai_client: Optional[AsyncOpenAI] = None) -> BaseVerifier:
    """Get the appropriate verifier for a benchmark."""
    if "finsearchcomp" in benchmark_name:
        return FinSearchCompVerifier(openai_client)
    if "gaia" in benchmark_name and "gaia-validation-text" not in benchmark_name:
        return GAIAVerifier()
    if "simpleqa" in benchmark_name:
        return SimpleQAVerifier(openai_client)
    if "xbench" in benchmark_name:
        return XBenchVerifier(openai_client)
    if "browsecomp" in benchmark_name or "hle" in benchmark_name:
        return HLEVerifier(openai_client)
    return None


async def verify_answer_for_benchmark(
    openai_client: AsyncOpenAI,
    benchmark_name: str,
    question: str,
    target: str,
    predicted_answer: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Verify answer using appropriate evaluation method for the dataset."""
    try:
        # FinSearchComp metadata validation
        if "finsearchcomp" in benchmark_name:
            if not metadata or not metadata.get("judge_prompt_template") or not metadata.get("judge_system_prompt"):
                print("Warning: FinSearchComp requires metadata with judge prompts")
                return EVAL_NOT_ATTEMPTED
        
        verifier = get_verifier(benchmark_name, openai_client)
        return await verifier.verify(question, target, predicted_answer, metadata)
    except Exception as e:
        print(f"Evaluation failed: {e}")
        return EVAL_NOT_ATTEMPTED


# ============================================================================
# SimpleQA Verifier
# ============================================================================

class SimpleQAVerifier(BaseVerifier):
    """Verifier for SimpleQA benchmark using LLM-based evaluation."""
    
    MAX_TOKENS = 2
    
    @property
    def EVALUATION_PROMPT(self) -> str:
        return get_eval_prompt("simpleqa", "judge_prompt")
    
    @retry(wait=wait_exponential(multiplier=RETRY_MULTIPLIER), stop=stop_after_attempt(RETRY_MAX_ATTEMPTS))
    async def verify(self, question: str, target: str, predicted_answer: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Verify answer using SimpleQA evaluation protocol."""
        CHOICE_MAP = {"A": EVAL_CORRECT, "B": EVAL_INCORRECT, "C": EVAL_NOT_ATTEMPTED}
        
        messages = [{"role": "user", "content": self.EVALUATION_PROMPT.format(question, target, predicted_answer)}]
        
        response = await self.openai_client.chat.completions.create(
            model=LLM_GPT4O_MINI,
            messages=messages,
            max_completion_tokens=self.MAX_TOKENS,
            temperature=TEMP_DETERMINISTIC
        )
        
        content = response.choices[0].message.content
        match = re.search(r"(A|B|C)", content)
        
        if match:
            return CHOICE_MAP[match.group(0)]
        raise Exception(f"SimpleQA LLM evaluation failed: {content}")

# ============================================================================
# XBench Verifier (Chinese)
# ============================================================================

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
    
    @retry(wait=wait_exponential(multiplier=RETRY_MULTIPLIER), stop=stop_after_attempt(RETRY_MAX_ATTEMPTS))
    async def verify(self, question: str, target: str, predicted_answer: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Verify answer using XBench-style LLM judge (Chinese evaluation)."""
        prompt = self.JUDGE_PROMPT.format(question=question, correct_answer=target, response=predicted_answer)
        
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


# ============================================================================
# HLE Verifier
# ============================================================================

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
    
    @retry(wait=wait_exponential(multiplier=RETRY_MULTIPLIER), stop=stop_after_attempt(RETRY_MAX_ATTEMPTS))
    async def verify(self, question: str, target: str, predicted_answer: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Verify answer using HLE-style LLM judge."""
        prompt = self.JUDGE_PROMPT.format(question=question, correct_answer=target, response=predicted_answer)
        
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


# ============================================================================
# GAIA Verifier (Exact Matching with Normalization)
# ============================================================================

class GAIAVerifier(BaseVerifier):
    """Verifier for GAIA benchmark using exact matching with normalization."""
    
    async def verify(self, question: str, target: str, predicted_answer: str, metadata: Optional[Dict[str, Any]] = None) -> str:
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
                comparisons.append(self._normalize_number_str(ma_elem) == float(gt_elem))
            else:
                comparisons.append(self._normalize_str(ma_elem, False) == self._normalize_str(gt_elem, False))
        
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


# ============================================================================
# FinSearchComp Verifier (Dynamic Judge Prompts)
# ============================================================================

class FinSearchCompVerifier(BaseVerifier):
    """Verifier for FinSearchComp benchmark using dynamic LLM judge prompts."""
    
    MAX_TOKENS = 2048
    
    @retry(wait=wait_exponential(multiplier=RETRY_MULTIPLIER), stop=stop_after_attempt(RETRY_MAX_ATTEMPTS))
    async def verify(self, question: str, target: str, predicted_answer: str, metadata: Optional[Dict[str, Any]] = None) -> str:
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
