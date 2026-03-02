# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Evaluation utilities for benchmark tasks with JSONL-based infrastructure."""

import json
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union

from omegaconf import DictConfig
from openai import AsyncOpenAI

from .verifiers import (
    EVAL_ERROR,
    EVAL_NOT_ATTEMPTED,
    BaseVerifier,
    BrowseCompEnVerifier,
    BrowseCompZhVerifier,
    FinSearchCompVerifier,
    GAIACommonVerifier,
    HLEVerifier,
    SimpleQAVerifier,
    XBenchVerifier,
)

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

# Invalid answer markers
INVALID_ANSWER_MARKERS = [
    "NO_ANSWER",
    "INSUFFICIENT_INFO",
    "CANNOT_DETERMINE",
    "None",
    "none",
    "N/A",
    "n/a",
    "NONE",
    "Unknown",
    "unknown",
    "UNKNOWN",
    r"No \boxed{} content found.",
]


def is_valid_box(final_boxed_answer: str) -> bool:
    """Check if the boxed answer is valid (not empty and not a placeholder)."""
    if not final_boxed_answer:
        return False
    return not any(marker in final_boxed_answer for marker in INVALID_ANSWER_MARKERS)


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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task_id,
            "task_question": self.task_question,
            "file_path": self.file_path,
            "ground_truth": self.ground_truth,
            "metadata": self.metadata.copy() if self.metadata else {},
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        """Create Task from dictionary."""
        return cls(
            task_id=data["task_id"],
            task_question=data["task_question"],
            file_path=data.get("file_path"),
            ground_truth=data.get("ground_truth", ""),
            metadata=data.get("metadata", {}),
        )


class AttemptResult:
    """Single attempt result for a benchmark task (one retry within an attempt)."""

    def __init__(
        self,
        task: Task,
        attempt_id: int,
        retry_id: int = 0,
        model_response: str = "",
        model_boxed_answer: str = "",
        status: str = STATUS_PENDING,
        log_path: Optional[Path] = None,
        judge_result: Optional[str] = None,
        is_correct: bool = False,
        error_message: Optional[str] = None,
        is_valid_box: bool = False,
        exceed_max_turn_summary: Optional[str] = None,
        used_exceed_max_turn_summaries: Optional[List[str]] = None,
        verifier_name: Optional[str] = None,
    ):
        self.task = task
        self.attempt_id = attempt_id
        self.retry_id = retry_id
        self.model_response = model_response
        self.model_boxed_answer = model_boxed_answer
        self.status = status
        self.log_path = log_path
        self.judge_result = judge_result
        self.is_correct = is_correct
        self.error_message = error_message
        self.is_valid_box = is_valid_box
        self.exceed_max_turn_summary = exceed_max_turn_summary
        self.verifier_name = verifier_name
        self.used_exceed_max_turn_summaries = used_exceed_max_turn_summaries or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "task_id": self.task.task_id,
            "attempt_id": self.attempt_id,
            "retry_id": self.retry_id,
            "model_response": self.model_response,
            "model_boxed_answer": self.model_boxed_answer,
            "status": self.status,
            "log_path": str(self.log_path) if self.log_path else None,
            "judge_result": self.judge_result,
            "is_correct": self.is_correct,
            "error_message": self.error_message,
            "is_valid_box": self.is_valid_box,
            "exceed_max_turn_summary": self.exceed_max_turn_summary,
            "used_exceed_max_turn_summaries": self.used_exceed_max_turn_summaries,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], task: Task) -> "AttemptResult":
        """Create AttemptResult from dictionary."""
        return cls(
            task=task,
            attempt_id=data.get("attempt_id", 0),
            retry_id=data.get("retry_id", 0),
            model_response=data.get("model_response", ""),
            model_boxed_answer=data.get("model_boxed_answer", ""),
            status=data.get("status", STATUS_PENDING),
            log_path=Path(data["log_path"]) if data.get("log_path") else None,
            judge_result=data.get("judge_result"),
            is_correct=data.get("is_correct", False),
            error_message=data.get("error_message"),
            is_valid_box=data.get("is_valid_box", False),
            exceed_max_turn_summary=data.get("exceed_max_turn_summary"),
            used_exceed_max_turn_summaries=data.get("used_exceed_max_turn_summaries"),
        )

    def update_from_response(self, response: Dict[str, Any], log_path: Path):
        """Update with response data from agent.run()."""
        self.model_response = response
        self.model_boxed_answer = response.get("final_boxed_answer", "")
        self.is_valid_box = is_valid_box(self.model_boxed_answer)
        self.exceed_max_turn_summary = response.get("exceed_max_turn_summary")
        self.status = STATUS_COMPLETED if self.model_boxed_answer else STATUS_FAILED
        self.log_path = log_path

    async def update_with_evaluation(
        self, evaluation_result: str, verifier_name: Optional[str] = None
    ):
        """Update with evaluation result and log file."""
        self.judge_result = evaluation_result
        self.is_correct = evaluation_result == "CORRECT"
        self.verifier_name = verifier_name
        if self.log_path:
            await self.update_log_with_evaluation(evaluation_result, verifier_name)

    async def update_log_with_evaluation(
        self, evaluation_result: str, verifier_name: Optional[str] = None
    ):
        """Update log file with evaluation result and verifier name."""
        if not self.log_path:
            return

        try:
            log_file = Path(self.log_path)
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)

            if "task_meta" not in log_data:
                log_data["task_meta"] = {}
            log_data["task_meta"]["judge_result"] = evaluation_result
            if verifier_name:
                log_data["task_meta"]["verifier_name"] = verifier_name

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
        self.total_attempts: int = 0
        self.total_retries: int = 0

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
        for field_name in ["log_path", "file_path"]:
            if isinstance(result.get(field_name), Path):
                result[field_name] = str(result[field_name])

        # Convert AttemptResult objects to dicts
        for i, attempt in enumerate(result.get("attempts", [])):
            if isinstance(attempt, AttemptResult):
                result["attempts"][i] = attempt.to_dict()
            elif isinstance(attempt, dict) and isinstance(
                attempt.get("log_path"), Path
            ):
                attempt["log_path"] = str(attempt["log_path"])

        return result

    def update_with_attempt(self, attempt_result: AttemptResult):
        """Update with attempt result."""
        self.attempts.append(attempt_result)
        attempt_num = len(self.attempts)

        # Update main result with first or successful attempt
        if attempt_num == 1 or (
            not self.model_boxed_answer and attempt_result.status == STATUS_COMPLETED
        ):
            self.model_response = attempt_result.model_response
            self.model_boxed_answer = attempt_result.model_boxed_answer
            self.log_path = attempt_result.log_path
            self.status = attempt_result.status
            self.error_message = attempt_result.error_message

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskResult":
        """Create TaskResult from dictionary."""
        task = Task(
            task_id=data["task_id"],
            task_question=data["task_question"],
            file_path=data.get("file_path"),
            ground_truth=data.get("ground_truth", ""),
            metadata=data.get("metadata", {}),
        )
        result = cls(task=task)
        result.model_response = data.get("model_response", "")
        result.model_boxed_answer = data.get("model_boxed_answer", "")
        result.status = data.get("status", STATUS_PENDING)
        result.error_message = data.get("error_message", "")
        result.judge_result = data.get("judge_result")
        result.log_path = data.get("log_path")
        result.pass_at_k_success = data.get("pass_at_k_success", False)
        result.total_attempts = data.get("total_attempts", 0)
        result.total_retries = data.get("total_retries", 0)
        result.attempts = [
            AttemptResult.from_dict(a, task) for a in data.get("attempts", [])
        ]
        return result


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
        # Support custom base_url for OpenAI-compatible APIs
        openai_base_url = cfg.get("openai_base_url", None)
        self.evaluation_llm = AsyncOpenAI(
            api_key=cfg.openai_api_key,
            base_url=openai_base_url if openai_base_url else None,
        )
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
                check=True,
                capture_output=True,
                text=True,
            )

            # Extract to parent directory (zip contains dataset folder)
            # This ensures final structure is data/{dataset_name}/, not data/{dataset_name}/{dataset_name}/
            subprocess.run(
                ["unzip", "-P", "pf4*", "-d", str(self.data_dir.parent), str(zip_file)],
                check=True,
                capture_output=True,
                text=True,
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

        print(
            f"Calculating pass@{self.pass_at_k} accuracy for {len(results)} results..."
        )

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

    def _print_accuracy_summary(
        self, correct_count: int, total_count: int, accuracy: float
    ) -> None:
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
                evaluation_result, verifier_name = await verify_answer_for_benchmark(
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
                verifier_name = None

            await attempt_result.update_with_evaluation(
                evaluation_result, verifier_name
            )

        status = (
            "✅ CORRECT"
            if attempt_result.is_correct
            else f"❌ INCORRECT ({attempt_result.judge_result})"
        )
        print(f"    {status}")
        return attempt_result


# ============================================================================
# Verifier Factory and Router
# ============================================================================


def get_verifier(
    benchmark_name: str, openai_client: Optional[AsyncOpenAI] = None
) -> BaseVerifier:
    """Get the appropriate verifier for a benchmark.

    Routing aligned with MiroThinker's _verify_answer_for_datasets_core:
    - gaia-validation / gaia-* → GAIACommonVerifier (gpt-4.1, simple equivalence)
    - browsecomp-zh → BrowseCompZhVerifier (gpt-4.1, Chinese BC prompt)
    - browsecomp / browsecomp-en → BrowseCompEnVerifier (gpt-4.1, English BC prompt)
    - hle / hle-* → HLEVerifier (o3-mini, structured Pydantic)
    - xbench / xbench-ds → XBenchVerifier (gpt-4.1, free-text regex)
    - simpleqa → SimpleQAVerifier (gpt-4.1, A/B/C)
    - webwalkerqa / frames / seal → GAIACommonVerifier (gpt-4.1, simple equivalence)
    - finsearchcomp → FinSearchCompVerifier (dynamic prompts)
    - default → GAIACommonVerifier (gpt-4.1, simple equivalence)
    """
    if "gaia" in benchmark_name:
        return GAIACommonVerifier(openai_client)
    if "finsearchcomp" in benchmark_name:
        return FinSearchCompVerifier(openai_client)
    if "simpleqa" in benchmark_name:
        return SimpleQAVerifier(openai_client)
    if "xbench" in benchmark_name:
        return XBenchVerifier(openai_client)
    if "browsecomp-zh" in benchmark_name:
        return BrowseCompZhVerifier(openai_client)
    if "browsecomp" in benchmark_name:
        return BrowseCompEnVerifier(openai_client)
    if "hle" in benchmark_name:
        return HLEVerifier(openai_client)
    # webwalkerqa, frames, seal use same equivalence judge as GAIA
    if any(name in benchmark_name for name in ["webwalkerqa", "frames", "seal"]):
        return GAIACommonVerifier(openai_client)
    # Default to GAIACommonVerifier (gpt-4.1, simple equivalence) aligned with MiroThinker
    return GAIACommonVerifier(openai_client)


async def verify_answer_for_benchmark(
    openai_client: AsyncOpenAI,
    benchmark_name: str,
    question: str,
    target: str,
    predicted_answer: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> tuple[str, str]:
    """Verify answer using appropriate evaluation method for the dataset.

    Returns:
        tuple[str, str]: (evaluation_result, verifier_name)
    """
    try:
        # FinSearchComp metadata validation
        if "finsearchcomp" in benchmark_name:
            if (
                not metadata
                or not metadata.get("judge_prompt_template")
                or not metadata.get("judge_system_prompt")
            ):
                print("Warning: FinSearchComp requires metadata with judge prompts")
                return EVAL_NOT_ATTEMPTED, "None"

        verifier = get_verifier(benchmark_name, openai_client)
        verifier_name = verifier.__class__.__name__
        result = await verifier.verify(question, target, predicted_answer, metadata)
        return result, verifier_name
    except Exception as e:
        print(f"Evaluation failed: {e}")
        return EVAL_NOT_ATTEMPTED, "None"
