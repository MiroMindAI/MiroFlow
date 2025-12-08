# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import os
import signal
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, TypedDict
import random

import dotenv
import hydra
import openai
from omegaconf import DictConfig, OmegaConf

from utils.eval_utils import verify_answer_for_datasets
from src.logging.logger import (
    bootstrap_logger,
    task_logging_context,
    init_logging_for_benchmark_evaluation,
)
from config import config_name, config_path
from src.core.pipeline import (
    create_pipeline_components,
    execute_task_pipeline,
)

init_logging_for_benchmark_evaluation(print_task_logs=False)


class TaskStatus(StrEnum):
    PENDING = "pending"
    RUN_FAILED = "run_failed"
    RUN_COMPLETED = "run_completed"
    RESULT_JUDGED = "result_judged"


@dataclass
class BenchmarkTask:
    """Generic benchmark task data structure"""

    task_id: str
    task_question: str
    ground_truth: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    model_response: str = ""
    model_boxed_answer: str = ""
    status: TaskStatus = TaskStatus.PENDING
    # status: str = "pending"  # pending, success, failed


class AttemptStats(TypedDict):
    attempt_number: int
    model_response: str
    model_boxed_answer: str
    status: TaskStatus
    log_file_path: Optional[Path]
    judge_result: Optional[str]
    is_correct: bool
    error_message: Optional[str]


@dataclass
class BenchmarkResult:
    """Generic benchmark evaluation result structure"""

    task_id: str
    task_question: str
    ground_truth: str
    file_path: Optional[str]
    model_response: str
    model_boxed_answer: str
    status: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: str = ""
    judge_result: Optional[str] = None
    log_file_path: Optional[Path] = None
    # Pass@K support fields
    attempts: List[AttemptStats] = field(default_factory=list)  # Store all attempts
    pass_at_k_success: bool = False  # Whether task passed using pass@k evaluation
    k_value: int = 1  # The k value used for this evaluation

    def to_dict(self):
        """Convert the object to a serializable dictionary."""
        result = self.__dict__.copy()  # Copy the object's dictionary
        # Convert Path objects to string
        if isinstance(result.get("log_file_path"), Path):
            result["log_file_path"] = str(result["log_file_path"])
        if isinstance(result.get("file_path"), Path):
            result["file_path"] = str(result["file_path"])
        # Convert any Path objects inside the attempts list
        for attempt in result.get("attempts", []):
            if isinstance(attempt.get("log_file_path"), Path):
                attempt["log_file_path"] = str(attempt["log_file_path"])
        return result


class BenchmarkEvaluator(ABC):
    """Abstract base class for benchmark evaluators"""

    def __init__(self, data_dir: str, benchmark_name: str, cfg: DictConfig):
        """
        Initialize benchmark evaluator

        Args:
            data_dir: Path to benchmark data directory
            benchmark_name: Name of the benchmark
            cfg: The Hydra configuration object
        """
        self.data_dir = Path(data_dir)
        self.benchmark_name = benchmark_name
        self.cfg = cfg
        self.pass_at_k = cfg.benchmark.execution.get("pass_at_k", 1)
        self.output_dir = Path(cfg.output_dir).absolute()
        if not self.output_dir.exists():
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"Created output directory: {self.output_dir}")
        self.evaluation_llm = openai.AsyncOpenAI(api_key=cfg.benchmark.openai_api_key)
        self.tasks: List[BenchmarkTask] = []
        self.results: List[BenchmarkResult] = []

        # Initialize pipeline components
        logs_dir = self.get_log_dir()
        print("Initializing pipeline components...")
        (
            self.main_agent_tool_manager,
            self.sub_agent_tool_managers,
            self.output_formatter,
        ) = create_pipeline_components(cfg, logs_dir=str(logs_dir))
        print(
            f"Pipeline components initialized successfully! Using pass@{self.pass_at_k}"
        )

    @abstractmethod
    def load_tasks(self) -> List[BenchmarkTask]:
        """Load benchmark tasks from data files"""
        raise NotImplementedError("Subclasses must implement this method")

    @abstractmethod
    def prepare_task_description(
        self, task: BenchmarkTask
    ) -> Tuple[str, Optional[str]]:
        """Prepare task description and file path for the agent"""
        raise NotImplementedError("Subclasses must implement this method")

    def get_log_dir(self) -> Path:
        """Get the log directory for the current benchmark and model."""
        return Path(self.cfg.output_dir)

    async def run_single_task(self, task: BenchmarkTask) -> BenchmarkResult:
        """
        Run inference for a single benchmark task with pass@k support

        Args:
            task: BenchmarkTask object

        Returns:
            BenchmarkResult object
        """
        print(f"Processing task {task.task_id} with pass@{self.pass_at_k}")

        result = BenchmarkResult(
            task_id=task.task_id,
            task_question=task.task_question,
            ground_truth=task.ground_truth,
            file_path=task.file_path,
            model_response="",
            model_boxed_answer="",
            status="pending",
            metadata=task.metadata.copy(),
            error_message="",
            judge_result=None,
            log_file_path=None,
            attempts=[],
            pass_at_k_success=False,
            k_value=self.pass_at_k,
        )

        found_correct_answer = False

        # Print debug info about log directory
        print(f"  Current result directory: {self.output_dir}")
        print(f"  Current task log directory: {self.output_dir}/task_logs")

        try:
            # Prepare task
            task_description, task_file_path = self.prepare_task_description(task)

            # Run up to k attempts (with early stopping when correct answer found)
            for attempt in range(1, self.pass_at_k + 1):
                print(f"  Attempt {attempt}/{self.pass_at_k} for task {task.task_id}")

                attempt_result = self.scan_latest_attempt(task, attempt)
                # Run inference if no existing result
                if attempt_result["status"] in (
                    TaskStatus.PENDING,
                    TaskStatus.RUN_FAILED,
                ):
                    try:
                        (
                            response,
                            final_boxed_answer,
                            log_file_path,
                        ) = await execute_task_pipeline(
                            cfg=self.cfg,
                            task_id=f"{task.task_id}",
                            task_name=f"{task.task_id}",
                            task_file_name=task_file_path,
                            task_description=task_description,
                            main_agent_tool_manager=self.main_agent_tool_manager,
                            sub_agent_tool_managers=self.sub_agent_tool_managers,
                            output_formatter=self.output_formatter,
                            ground_truth=task.ground_truth,
                            metadata=task.metadata,
                            log_path=self.output_dir
                            / f"task_{task.task_id}_attempt_{attempt}.json",
                        )

                        attempt_result["model_response"] = response if response else ""
                        attempt_result["log_file_path"] = log_file_path
                        if final_boxed_answer:
                            attempt_result["model_boxed_answer"] = final_boxed_answer
                            attempt_result["status"] = TaskStatus.RUN_COMPLETED
                        else:
                            attempt_result["model_boxed_answer"] = final_boxed_answer
                            attempt_result["status"] = TaskStatus.RUN_FAILED

                    except Exception as e:
                        attempt_result["status"] = TaskStatus.RUN_FAILED
                        attempt_result["error_message"] = str(e)
                        print(f"    Error in attempt {attempt}: {e}")

                # Perform LLM verification if we have an answer and haven't verified yet
                if (
                    attempt_result["status"] == TaskStatus.RUN_COMPLETED
                    or attempt_result["judge_result"] == "NOT_ATTEMPTED"
                ):
                    # if attempt_result["status"] == TaskStatus.RUN_COMPLETED:
                    print(f"    Verifying answer for attempt {attempt}...")
                    try:
                        evaluation_result = await verify_answer_for_datasets(
                            openai_client=self.evaluation_llm,
                            benchmark_name=self.benchmark_name,
                            question=task.task_question,
                            target=task.ground_truth,
                            predicted_answer=attempt_result["model_boxed_answer"],
                            metadata=task.metadata,
                        )
                        attempt_result["judge_result"] = evaluation_result
                        attempt_result["is_correct"] = evaluation_result == "CORRECT"

                        # Update the log file with verification result
                        if "log_file_path" in attempt_result and isinstance(
                            attempt_result["log_file_path"], Path
                        ):
                            await self._update_log_file_with_evaluation(
                                attempt_result["log_file_path"], evaluation_result
                            )

                        if attempt_result["is_correct"]:
                            print(f"    ✅ Attempt {attempt}: CORRECT!")
                            found_correct_answer = True
                        else:
                            print(
                                f"    ❌ Attempt {attempt}: INCORRECT ({evaluation_result})"
                            )

                    except Exception as e:
                        print(f"    Error verifying attempt {attempt}: {e}")
                        attempt_result["judge_result"] = "ERROR"
                        attempt_result["is_correct"] = False

                if attempt_result["is_correct"]:
                    print(f"    ✅ Attempt {attempt}: CORRECT (cached)")
                    found_correct_answer = True
                elif attempt_result["judge_result"]:
                    print(
                        f"    ❌ Attempt {attempt}: INCORRECT (cached: {attempt_result['judge_result']})"
                    )
                else:
                    print(f"    ⚠️  Attempt {attempt}: No valid answer to verify")

                result.attempts.append(attempt_result)

                # Update main result with the first successful attempt or best attempt so far
                if attempt == 1 or (
                    attempt_result["status"] == TaskStatus.RUN_COMPLETED
                    and not result.model_boxed_answer
                ):
                    result.model_response = attempt_result["model_response"]
                    result.model_boxed_answer = attempt_result["model_boxed_answer"]
                    result.log_file_path = attempt_result["log_file_path"]
                    result.status = attempt_result["status"]
                    if attempt_result["error_message"] is not None:
                        result.error_message = attempt_result["error_message"]

                # Early stopping: if we found a correct answer, we can stop
                if found_correct_answer:
                    print(
                        f"    🎯 Found correct answer! Stopping early after {attempt} attempts."
                    )
                    break

        except Exception as e:
            result.error_message = str(e)
            result.status = "failed"
            print(f"Error processing task {task.task_id}: {e}")

        finally:
            result.pass_at_k_success = found_correct_answer

            # Set main result LLM judge result based on pass@k outcome
            if found_correct_answer:
                result.judge_result = "PASS_AT_K_SUCCESS"
            else:
                result.judge_result = "PASS_AT_K_FAILED"

            print(f"Task {task.task_id} completed with {len(result.attempts)} attempts")
            print(
                f"    Pass@{self.pass_at_k} result: {'✅ SUCCESS' if found_correct_answer else '❌ FAILED'}"
            )

        return result

    def scan_latest_attempt(self, task: BenchmarkTask, attempt: int) -> AttemptStats:
        """check filesystem for latest attempt"""
        attempt_result: AttemptStats = {
            "attempt_number": attempt,
            "model_response": "",
            "model_boxed_answer": "",
            "status": TaskStatus.PENDING,
            "log_file_path": None,
            "judge_result": None,
            "is_correct": False,
            "error_message": None,
        }
        trace_filename_pattern = f"task_{task.task_id}_attempt_{attempt}.json"
        matched_logs = self.output_dir.glob(trace_filename_pattern)
        sorted_logs = sorted(matched_logs, reverse=True)
        if len(sorted_logs) == 0:
            return attempt_result
        latest_log = sorted_logs[-1]
        attempt_result["status"] = TaskStatus.RUN_FAILED
        attempt_result["log_file_path"] = latest_log
        print(f"    Found existing log for attempt {attempt}: {latest_log.name}")

        with open(latest_log) as f:
            log_data = json.loads(f.read())
            if log_data.get("final_boxed_answer"):
                attempt_result["status"] = TaskStatus.RUN_COMPLETED
                attempt_result["model_boxed_answer"] = log_data["final_boxed_answer"]
                attempt_result["model_response"] = log_data.get("output", "")
                # Check if we already have LLM judge result in log
                if log_data.get("judge_result"):
                    attempt_result["status"] = TaskStatus.RESULT_JUDGED
                    attempt_result["judge_result"] = log_data["judge_result"]
                    attempt_result["is_correct"] = log_data["judge_result"] == "CORRECT"
                print(
                    f"    Loaded existing result: {attempt_result['model_boxed_answer']}"
                )
        return attempt_result

    async def run_parallel_inference(
        self, tasks: List[BenchmarkTask], max_concurrent: int = 3
    ) -> List[BenchmarkResult]:
        """Run inference on multiple tasks in parallel"""
        print(
            f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent}"
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def run_with_semaphore(task):
            async with semaphore:
                with task_logging_context(task.task_id, self.get_log_dir()):
                    result = await self.run_single_task(task)
                return result

        # Shuffle tasks to avoid order bias and improve balancing
        shuffled_tasks = tasks.copy()
        random.shuffle(shuffled_tasks)

        # Run tasks in parallel
        results = await asyncio.gather(
            *[run_with_semaphore(task) for task in shuffled_tasks],
            return_exceptions=True,
        )

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                print(f"Exception in task {shuffled_tasks[i].task_id}: {result}")
                error_result = BenchmarkResult(
                    task_id=shuffled_tasks[i].task_id,
                    task_question=shuffled_tasks[i].task_question,
                    ground_truth=shuffled_tasks[i].ground_truth,
                    file_path=shuffled_tasks[i].file_path,
                    model_response="",
                    model_boxed_answer="",
                    status="failed",
                    metadata=shuffled_tasks[i].metadata.copy(),
                    error_message=str(result),
                    judge_result=None,
                    log_file_path=None,
                    attempts=[],
                    pass_at_k_success=False,
                    k_value=self.pass_at_k,
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        self.results = processed_results
        return processed_results

    def save_results(self, output_path: Path) -> Path:
        """Save evaluation results to JSONL file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for result in self.results:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

        print(f"Results saved to {output_path}")
        return output_path

    async def evaluate_accuracy(self) -> float:
        """Evaluate pass@k accuracy (verification already done in run_single_task)"""
        if not self.results:
            print("No results to evaluate")
            return 0.0

        print(
            f"Calculating pass@{self.pass_at_k} accuracy for {len(self.results)} results..."
        )

        correct_count = 0
        total_count = 0

        for result in self.results:
            total_count += 1

            # Display task results
            print(f"\nTask {result.task_id}:")
            print(f"  Attempts: {len(result.attempts)}")
            print(
                f"  Pass@{self.pass_at_k}: {'✅ SUCCESS' if result.pass_at_k_success else '❌ FAILED'}"
            )

            # Show details of each attempt
            for attempt in result.attempts:
                attempt_num = attempt.get("attempt_number", "?")
                judge_result = attempt.get("judge_result", "NOT_VERIFIED")
                is_correct = attempt.get("is_correct", False)
                status_icon = (
                    "✅"
                    if is_correct
                    else "❌"
                    if judge_result != "NOT_VERIFIED"
                    else "⚠️"
                )
                print(f"    Attempt {attempt_num}: {status_icon} {judge_result}")
                if attempt.get("model_boxed_answer"):
                    print(f"      Answer: {attempt['model_boxed_answer']}")

            print("  " + "=" * 50)
            print(f"  Reference: {result.ground_truth}")
            print("  " + "=" * 50)

            if result.pass_at_k_success:
                correct_count += 1

        pass_at_k_accuracy = correct_count / total_count if total_count > 0 else 0.0

        print(f"\nPass@{self.pass_at_k} Final Results:")
        print(f"Tasks passed: {correct_count}/{total_count}")
        print(f"Pass@{self.pass_at_k} Accuracy: {pass_at_k_accuracy:.2%}")

        return pass_at_k_accuracy

    async def _update_log_file_with_evaluation(
        self, log_file_path: Path, evaluation_result: str
    ):
        """Helper method to update log file with evaluation result"""
        try:
            log_file = Path(log_file_path)
            # Read existing data
            with open(log_file, "r", encoding="utf-8") as f:
                log_data = json.load(f)

            # Update with evaluation result
            log_data["judge_result"] = evaluation_result

            # Write to a temporary file and then atomically replace
            temp_log_file = log_file.with_suffix(f"{log_file.suffix}.tmp")
            with open(temp_log_file, "w", encoding="utf-8") as f:
                json.dump(log_data, f, indent=2, ensure_ascii=False)

            os.replace(temp_log_file, log_file)
            print(f"    Updated log file {log_file.name} with evaluation result.")
        except Exception as e:
            print(f"    Error updating log file {log_file_path}: {e}")


class JSONLDatasetEvaluator(BenchmarkEvaluator):
    """benchmark evaluator for Gaia like dataset."""

    def __init__(
        self,
        data_dir: str,
        benchmark_name: str,
        cfg: DictConfig,
        metadata_file: str,
        parse_func: Callable[[str], BenchmarkTask],
        filter_func: Callable[[BenchmarkTask], bool],
    ):
        """
        dataset format:
        - a FOLDER (`data_dir`) with a METADATA file (`metadata_file`) and many other binary files.
        - METADATA file are newline separated json objects, parsed by `parse_func` into `BenchmarkTask` objects.
        - `filter_func` is used to filter tasks based on a condition.
        - binary files are referenced by `BenchmarkTask.file_path`.

        Args:
            data_dir: Path to benchmark data directory
            benchmark_name: Name of the benchmark
            cfg: The Hydra configuration object
            parse_func: Function to parse a line of data into a BenchmarkTask object
            filter_func: Function to filter tasks based on a condition
        """
        super().__init__(data_dir=data_dir, benchmark_name=benchmark_name, cfg=cfg)
        self.metadata_file = self.data_dir / metadata_file
        self.parse_func = parse_func
        self.filter_func = filter_func
        self.tasks: List[BenchmarkTask] = []
        self.results: List[BenchmarkResult] = []

    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Load benchmark tasks from metadata.jsonl

        Returns:
            List of BenchmarkTask objects
        """
        print(f"Loading tasks from {self.metadata_file}")

        if not self.metadata_file.exists():
            raise FileNotFoundError(f"Metadata file not found: {self.metadata_file}")

        tasks = []
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                try:
                    task = self.parse_func(line.strip())
                    if self.filter_func(task):
                        tasks.append(task)

                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {i + 1}: {e}")
                    continue
        tasks = tasks[: self.cfg.benchmark.execution.max_tasks]
        self.tasks = tasks
        print(f"Loaded {len(tasks)} tasks")
        return tasks

    def prepare_task_description(
        self, task: BenchmarkTask
    ) -> Tuple[str, Optional[str]]:
        if task.file_path is None:
            return task.task_question, None

        path = Path(task.file_path)
        # check if task.file_path is a relative path
        if path.is_absolute():
            return task.task_question, str(path)

        # Build complete file path: data directory + relative path
        full_file_path = Path(self.data_dir) / path
        return task.task_question, str(full_file_path)


async def entrypoint(cfg: DictConfig) -> float:
    """
    Main entry point for running benchmarks with Hydra.
    """
    print("Benchmark configuration:\n", OmegaConf.to_yaml(cfg, resolve=True))

    def parse_func(x: str) -> BenchmarkTask:
        data = json.loads(x)
        if isinstance(data.get("task_id"), (str, bytes, os.PathLike)) is False:
            try:
                data["task_id"] = str(data["task_id"])
            except TypeError:
                raise TypeError(
                    "expected task_id to be a string, bytes or os.PathLike object"
                )
        return BenchmarkTask(
            task_id=data["task_id"],
            task_question=data["task_question"],
            ground_truth=data["ground_truth"],
            file_path=data.get("file_path"),
            metadata=data.get("metadata", {}),
        )

    def filter_func(x: BenchmarkTask) -> bool:
        if len(cfg.benchmark.data.whitelist) > 0:
            return x.task_id in cfg.benchmark.data.whitelist
        else:
            return True

    evaluator = JSONLDatasetEvaluator(
        data_dir=cfg.benchmark.data.data_dir,
        benchmark_name=cfg.benchmark.name,
        cfg=cfg,
        metadata_file=cfg.benchmark.data.metadata_file,
        parse_func=parse_func,
        filter_func=filter_func,
    )

    """
    Run the full benchmark evaluation process
    """
    print(f"Starting evaluation for benchmark: {cfg.benchmark.name}")

    # Load tasks
    tasks = evaluator.load_tasks()
    if len(evaluator.tasks) == 0:
        print("No tasks loaded. Exiting.")
        return 0.0

    # Run inference
    print(
        f"\nStarting parallel inference with {cfg.benchmark.execution.max_concurrent} concurrent tasks..."
    )
    print(f"Using pass@{evaluator.pass_at_k} evaluation...")
    await evaluator.run_parallel_inference(
        tasks,
        max_concurrent=cfg.benchmark.execution.max_concurrent,
    )

    # Evaluate accuracy
    print("Evaluating accuracy...")
    accuracy = await evaluator.evaluate_accuracy()
    print(f"\nOverall pass@{evaluator.pass_at_k} accuracy: {accuracy:.2%}")
    # Save results

    output_filename = "benchmark_results.jsonl"

    # Construct the full path in the correct log directory
    log_dir = evaluator.output_dir
    results_path = log_dir / output_filename

    evaluator.save_results(results_path)
    print(f"\nEvaluation completed! Results saved to {results_path}")
    # save accuracy to a file
    accuracy_file = (
        results_path.parent
        / f"{results_path.stem}_pass_at_{evaluator.pass_at_k}_accuracy.txt"
    )
    with open(accuracy_file, "w") as f:
        f.write(f"{accuracy:.2%}")

    return accuracy


def setup_hydra_output_dir(cfg: DictConfig, overrides: List[str]) -> DictConfig:
    """Manually creates a Hydra-like output directory and saves the configuration."""
    # Get the base output directory from config
    base_output_dir = Path(cfg.output_dir)

    run_output_dir = base_output_dir
    run_output_dir.mkdir(parents=True, exist_ok=True)

    # Save the composed configuration
    hydra_dir = run_output_dir / ".hydra"
    hydra_dir.mkdir(exist_ok=True)

    with open(hydra_dir / "config.yaml", "w", encoding="utf-8") as f:
        f.write(OmegaConf.to_yaml(cfg, resolve=False))
    with open(hydra_dir / "overrides.yaml", "w", encoding="utf-8") as f:
        f.write(OmegaConf.to_yaml(overrides))

    print(f"Hydra-like output directory created at: {run_output_dir}")
    return cfg


def signal_handler(signum, frame):
    """Force exit signal handler"""
    print(f"\n⚠️  Received interrupt signal {signum}, forcing immediate exit...")
    print("Program will terminate all operations immediately")
    os._exit(1)  # Force immediate exit


def main(*args, config_file_name: str = ""):
    # Register signal handlers for immediate response to Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    dotenv.load_dotenv()
    LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")

    # Support load from config_file_name
    if config_file_name:
        chosen_config_name = config_file_name
    else:
        chosen_config_name = config_name()

    with hydra.initialize_config_dir(
        config_dir=os.path.abspath(config_path()), version_base=None
    ):
        cfg = hydra.compose(config_name=chosen_config_name, overrides=list(args))
        cfg = setup_hydra_output_dir(cfg, list(args))

        _ = bootstrap_logger(level=LOGGER_LEVEL)
        # Tracing functionality removed - miroflow-contrib deleted
        asyncio.run(entrypoint(cfg))
