# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""
Evaluation utilities for benchmark tasks.

This module provides generic evaluation infrastructure for JSONL-based benchmarks,
including task loading, result management, and various LLM-based judging methods.
"""

import json
import os
import re
import string
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, TYPE_CHECKING

from omegaconf import DictConfig
from openai import AsyncOpenAI
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential
from src.utils.task_utils import AttemptStats, TaskStatus

# Type aliases for better readability
EvaluationResult = str  # One of: "CORRECT", "INCORRECT", "NOT_ATTEMPTED"
TaskParser = Callable[[str], "BenchmarkTask"]
TaskFilter = Callable[["BenchmarkTask"], bool]


# ============================================================================
# Types and Data Classes
# ============================================================================

@dataclass
class BenchmarkTask:
    """
    Generic benchmark task data structure.

    Attributes:
        task_id: Unique identifier for the task
        task_question: The question or prompt for the task
        ground_truth: Expected correct answer
        file_path: Optional path to associated file (e.g., binary, image)
        metadata: Additional task-specific metadata
        model_response: Model's generated response (populated during evaluation)
        model_boxed_answer: Extracted final answer from model response
        status: Current status of the task (PENDING, COMPLETED, etc.)
    """

    task_id: str
    task_question: str
    ground_truth: str
    file_path: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    model_response: str = ""
    model_boxed_answer: str = ""
    status: TaskStatus = TaskStatus.PENDING


class BenchmarkResult:
    """
    Generic benchmark evaluation result structure.

    Stores all information about a task's evaluation, including attempts,
    final status, and pass@k evaluation results.

    Attributes:
        task_id: Unique identifier for the task
        task_question: The question being evaluated
        ground_truth: Expected correct answer
        file_path: Optional path to associated file
        model_response: Final model response
        model_boxed_answer: Final extracted answer
        status: Evaluation status (pending, completed, failed, etc.)
        metadata: Additional task-specific metadata
        error_message: Error message if evaluation failed
        judge_result: Result from the evaluation judge
        log_file_path: Path to detailed evaluation logs
        attempts: List of all attempts made (for pass@k evaluation)
        pass_at_k_success: Whether task passed using pass@k evaluation
        k_value: The k value used for this evaluation
    """

    def __init__(self, cfg: DictConfig, task: BenchmarkTask):
        """
        Initialize BenchmarkResult from task and configuration.

        Args:
            cfg: Hydra configuration object containing benchmark settings
            task: BenchmarkTask object containing task information
        """
        self.task_id = task.task_id
        self.task_question = task.task_question
        self.ground_truth = task.ground_truth
        self.file_path = task.file_path
        self.model_response = ""
        self.model_boxed_answer = ""
        self.status = "pending"
        self.metadata = task.metadata.copy() if task.metadata else {}
        self.error_message = ""
        self.judge_result = None
        self.log_file_path = None
        self.attempts = []
        self.pass_at_k_success = False
        self.k_value = cfg.benchmark.execution.get("pass_at_k", 1)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result object to a serializable dictionary.

        Returns:
            Dictionary with all Path objects converted to strings
        """
        result = self.__dict__.copy()

        # Convert Path objects to strings
        path_fields = ["log_file_path", "file_path"]
        for field in path_fields:
            if isinstance(result.get(field), Path):
                result[field] = str(result[field])

        # Convert Path objects in attempts list
        for attempt in result.get("attempts", []):
            if isinstance(attempt.get("log_file_path"), Path):
                attempt["log_file_path"] = str(attempt["log_file_path"])

        return result


# ============================================================================
# Benchmark Evaluators
# ============================================================================

class BenchmarkEvaluator:
    """
    Generic benchmark evaluator for JSONL-based datasets.

    This evaluator provides a flexible framework for evaluating agent performance
    on benchmark tasks. It supports:

    - JSONL metadata files for task definitions
    - Optional binary/reference files (e.g., images, documents)
    - Customizable task parsing and filtering
    - Pass@k evaluation metrics
    - Multiple LLM-based evaluation judges

    Attributes:
        data_dir: Path to benchmark data directory
        benchmark_name: Name of the benchmark
        cfg: Hydra configuration object
        pass_at_k: Number of attempts allowed per task
        output_dir: Directory for saving results
        evaluation_llm: OpenAI client for LLM-based evaluation
        tasks: Loaded benchmark tasks
        results: Evaluation results for all tasks
        metadata_file: Path to JSONL metadata file
        parse_func: Function to parse JSONL lines into tasks
        filter_func: Function to filter tasks
    """

    def __init__(
        self,
        data_dir: str,
        benchmark_name: str,
        cfg: DictConfig,
        metadata_file: Optional[str] = None,
        parse_func: Optional[TaskParser] = None,
        filter_func: Optional[TaskFilter] = None,
    ):
        """
        Initialize benchmark evaluator.

        Args:
            data_dir: Path to benchmark data directory
            benchmark_name: Name of the benchmark
            cfg: Hydra configuration object
            metadata_file: Name of the JSONL metadata file (optional)
            parse_func: Function to parse a JSONL line into BenchmarkTask (optional)
            filter_func: Function to filter tasks (optional, defaults to accept all)
        """
        self.data_dir = Path(data_dir)
        self.benchmark_name = benchmark_name
        self.cfg = cfg
        self.pass_at_k = cfg.benchmark.execution.get("pass_at_k", 1)

        # Setup output directory
        self.output_dir = Path(cfg.output_dir).absolute()
        self._ensure_output_dir_exists()

        # Initialize OpenAI client for evaluation
        self.evaluation_llm = AsyncOpenAI(api_key=cfg.benchmark.openai_api_key)

        # Initialize task storage
        self.tasks: List[BenchmarkTask] = []
        self.results: List[BenchmarkResult] = []

        # JSONL dataset support
        self.metadata_file = self.data_dir / metadata_file if metadata_file else None
        self.parse_func = parse_func
        self.filter_func = filter_func if filter_func else lambda x: True

    def _ensure_output_dir_exists(self) -> None:
        """Create output directory if it doesn't exist."""
        if not self.output_dir.exists():
            os.makedirs(self.output_dir, exist_ok=True)
            print(f"Created output directory: {self.output_dir}")

    def load_tasks(self) -> List[BenchmarkTask]:
        """
        Load benchmark tasks from JSONL metadata file.

        Returns:
            List of BenchmarkTask objects (limited by max_tasks config)

        Raises:
            ValueError: If metadata_file or parse_func not provided
            FileNotFoundError: If metadata file doesn't exist
        """
        self._validate_load_requirements()

        print(f"Loading tasks from {self.metadata_file}")

        tasks = self._parse_tasks_from_file()
        tasks = self._apply_task_limit(tasks)

        self.tasks = tasks
        print(f"Loaded {len(tasks)} tasks")
        return tasks

    def _validate_load_requirements(self) -> None:
        """Validate that required components are present for loading tasks."""
        if not self.metadata_file:
            raise ValueError("metadata_file must be provided to load tasks")
        if not self.metadata_file.exists():
            raise FileNotFoundError(
                f"Metadata file not found: {self.metadata_file}")
        if not self.parse_func:
            raise ValueError("parse_func must be provided to load tasks")

    def _parse_tasks_from_file(self) -> List[BenchmarkTask]:
        """Parse tasks from JSONL file, applying filter function."""
        tasks = []
        with open(self.metadata_file, "r", encoding="utf-8") as f:
            for i, line in enumerate(f, start=1):
                try:
                    task = self.parse_func(line.strip())
                    if self.filter_func(task):
                        tasks.append(task)
                except json.JSONDecodeError as e:
                    print(f"Warning: Failed to parse line {i}: {e}")
                    continue
        return tasks

    def _apply_task_limit(self, tasks: List[BenchmarkTask]) -> List[BenchmarkTask]:
        """Limit tasks to max_tasks configuration."""
        max_tasks = self.cfg.benchmark.execution.max_tasks
        return tasks[:max_tasks]

    def prepare_task_description(
        self, task: BenchmarkTask
    ) -> Tuple[str, Optional[str]]:
        """
        Prepare task description and resolve file path for the agent.

        Args:
            task: BenchmarkTask object

        Returns:
            Tuple of (task_question, resolved_file_path)
        """
        if task.file_path is None:
            return task.task_question, None

        resolved_path = self._resolve_file_path(task.file_path)
        return task.task_question, str(resolved_path)

    def _resolve_file_path(self, file_path: str) -> Path:
        """
        Resolve file path to absolute path.

        Args:
            file_path: File path (absolute or relative)

        Returns:
            Absolute Path object
        """
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.data_dir / path

    def save_results(self, output_path: Path) -> Path:
        """Save evaluation results to JSONL file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            for result in self.results:
                f.write(json.dumps(result.to_dict(), ensure_ascii=False) + "\n")

        print(f"Results saved to {output_path}")
        return output_path

    async def evaluate_accuracy(self) -> float:
        """
        Evaluate pass@k accuracy across all results.

        Returns:
            Pass@k accuracy as a float between 0 and 1
        """
        if not self.results:
            print("No results to evaluate")
            return 0.0

        print(
            f"Calculating pass@{self.pass_at_k} accuracy for {len(self.results)} results...")

        correct_count = sum(
            1 for result in self.results if result.pass_at_k_success)
        total_count = len(self.results)

        # Display detailed results for each task
        for result in self.results:
            self._print_task_result(result)

        # Print summary
        accuracy = correct_count / total_count if total_count > 0 else 0.0
        self._print_accuracy_summary(correct_count, total_count, accuracy)

        return accuracy

    def _print_task_result(self, result: BenchmarkResult) -> None:
        """Print detailed results for a single task."""
        print(f"\nTask {result.task_id}:")
        print(f"  Attempts: {len(result.attempts)}")

        success_status = "✅ SUCCESS" if result.pass_at_k_success else "❌ FAILED"
        print(f"  Pass@{self.pass_at_k}: {success_status}")

        # Show details of each attempt
        for attempt in result.attempts:
            self._print_attempt_details(attempt)

        # Show ground truth reference
        print("  " + "=" * 50)
        print(f"  Reference: {result.ground_truth}")
        print("  " + "=" * 50)

    def _print_attempt_details(self, attempt: Dict[str, Any]) -> None:
        """Print details of a single attempt."""
        attempt_num = attempt.get("attempt_number", "?")
        judge_result = attempt.get("judge_result", "NOT_VERIFIED")
        is_correct = attempt.get("is_correct", False)

        status_icon = self._get_status_icon(is_correct, judge_result)
        print(f"    Attempt {attempt_num}: {status_icon} {judge_result}")

        if attempt.get("model_boxed_answer"):
            print(f"      Answer: {attempt['model_boxed_answer']}")

    @staticmethod
    def _get_status_icon(is_correct: bool, judge_result: str) -> str:
        """Get status icon based on correctness and judge result."""
        if is_correct:
            return "✅"
        elif judge_result != "NOT_VERIFIED":
            return "❌"
        else:
            return "⚠️"

    def _print_accuracy_summary(
        self, correct_count: int, total_count: int, accuracy: float
    ) -> None:
        """Print accuracy summary."""
        print(f"\nPass@{self.pass_at_k} Final Results:")
        print(f"Tasks passed: {correct_count}/{total_count}")
        print(f"Pass@{self.pass_at_k} Accuracy: {accuracy:.2%}")


# ============================================================================
# Evaluation Constants
# ============================================================================

# Evaluation result constants
EVAL_CORRECT = "CORRECT"
EVAL_INCORRECT = "INCORRECT"
EVAL_NOT_ATTEMPTED = "NOT_ATTEMPTED"

# LLM model constants
LLM_GPT4O_MINI = "gpt-4o-mini"
LLM_O3_MINI = "o3-mini-2025-01-31"
LLM_O3 = "o3"

# Temperature settings
TEMP_DETERMINISTIC = 0.0

# Retry settings
RETRY_MULTIPLIER = 5
RETRY_MAX_ATTEMPTS = 5


# ============================================================================
# Base Verifier Class
# ============================================================================

class BaseVerifier:
    """
    Base class for benchmark answer verifiers.
    
    Each benchmark should implement a concrete verifier class that inherits
    from this base class and implements the verify() method.
    """
    
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        """
        Initialize verifier.
        
        Args:
            openai_client: OpenAI client for LLM-based evaluation (optional)
        """
        self.openai_client = openai_client
    
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Verify if predicted answer matches the target answer.
        
        Args:
            question: The question being answered
            target: Ground truth answer
            predicted_answer: Model's predicted answer
            metadata: Optional metadata for specialized evaluation
        
        Returns:
            Evaluation result: "CORRECT", "INCORRECT", or "NOT_ATTEMPTED"
        """
        raise NotImplementedError("Subclasses must implement verify()")


# ============================================================================
# Verifier Factory and Router
# ============================================================================

def get_verifier(
    benchmark_name: str,
    openai_client: Optional[AsyncOpenAI] = None,
) -> BaseVerifier:
    """
    Get the appropriate verifier for a given benchmark.
    
    Args:
        benchmark_name: Name of the benchmark dataset
        openai_client: OpenAI client for LLM-based evaluation
    
    Returns:
        Appropriate verifier instance for the benchmark
    """
    # FinSearchComp with dynamic judge prompts
    if "finsearchcomp" in benchmark_name:
        return FinSearchCompVerifier(openai_client)
    
    # GAIA datasets (not gaia-validation-text)
    if "gaia" in benchmark_name and "gaia-validation-text" not in benchmark_name:
        return GAIAVerifier()
    
    # SimpleQA specific evaluation
    if "simpleqa" in benchmark_name:
        return SimpleQAVerifier(openai_client)
    
    # XBench specific evaluation
    if "xbench" in benchmark_name:
        return XBenchVerifier(openai_client)
    
    # BrowseComp-ZH 和 browsecomp-zh 都使用 HLEVerifier，其它默认
    if "browsecomp" in benchmark_name or "hle" in benchmark_name:
        return HLEVerifier(openai_client)
    
    return None


async def verify_answer_for_datasets(
    openai_client: AsyncOpenAI,
    benchmark_name: str,
    question: str,
    target: str,
    predicted_answer: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Verify answer using the appropriate evaluation method for the dataset.
    
    This function serves as a convenient router that automatically selects
    and uses the appropriate verifier based on the benchmark name.
    
    Args:
        openai_client: OpenAI client for LLM-based evaluation
        benchmark_name: Name of the benchmark dataset
        question: The question being answered
        target: Ground truth answer
        predicted_answer: Model's predicted answer
        metadata: Optional metadata for specialized evaluation
    
    Returns:
        Evaluation result: "CORRECT", "INCORRECT", or "NOT_ATTEMPTED"
    """
    try:
        # Special handling for FinSearchComp to check metadata requirements
        if "finsearchcomp" in benchmark_name:
            if metadata is None or \
                metadata.get("judge_prompt_template") is None or \
                metadata.get("judge_system_prompt") is None:
                print("Warning: FinSearchComp requires metadata with judge prompts")
                return EVAL_NOT_ATTEMPTED
        
        # Get appropriate verifier and verify answer
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
    
    EVALUATION_PROMPT = """
Your job is to look at a question, a gold target, and a predicted answer, and then assign a grade of either ["CORRECT", "INCORRECT", "NOT_ATTEMPTED"].
First, I will give examples of each grade, and then you will grade a new example.


The following are examples of CORRECT predicted answers.
```
Question: What are the names of Barack Obama's children?
Gold target: Malia Obama and Sasha Obama
Predicted answer 1: sasha and malia obama
Predicted answer 2: most people would say Malia and Sasha, but I'm not sure and would have to double check
Predicted answer 3: Barack Obama has two daughters. Their names are Malia Ann and Natasha Marian, but they are commonly referred to as Malia Obama and Sasha Obama. Malia was born on July 4, 1998, and Sasha was born on June 10, 2001.
```
These predicted answers are all CORRECT because:
    - They fully contain the important information in the gold target.
    - They do not contain any information that contradicts the gold target.
    - Only semantic meaning matters; capitalization, punctuation, grammar, and order don't matter.
    - Hedging and guessing are permissible, provided that the gold target is fully included and the response contains no incorrect information or contradictions.


The following are examples of INCORRECT predicted answers.
```
Question: What are the names of Barack Obama's children?
Gold target: Malia and Sasha
Predicted answer 1: Malia.
Predicted answer 2: Malia, Sasha, and Susan.
Predicted answer 3: Barack Obama does not have any children.
Predicted answer 4: I think it's either Malia and Sasha. Or it could be Malia and Jackie. Or it could be Joey and Malia.
Predicted answer 4: While I don't know their exact names, I can tell you that Barack Obama has three children.
Predicted answer 5: It's possible you may mean Betsy and Olivia. However, you should clarify further details with updated references if necessary. Is that the correct answer?
Predicted answer 6: It may be the case that Obama's child is named James. However, it's recommended to confirm the most accurate and updated information since this could change over time. This model may not always reflect the most current information.
```
These predicted answers are all INCORRECT because:
    - A factual statement in the answer contradicts the gold target. Incorrect statements that have some hedging (e.g., "it is possible that", "although i'm not sure, i think") are also considered incorrect.


The following are examples of NOT_ATTEMPTED predicted answers.
```
Question: What are the names of Barack Obama's children?
Gold target: Malia and Sasha
Predicted answer 1: I don't know.
Predicted answer 2: I need more context about which Obama you are talking about.
Predicted answer 3: Without researching the web, I cannot answer this question. However, I can tell you that Barack Obama has two children.
Predicted answer 4: Barack Obama has two children. I know that one of them is Malia, but I'm not sure about the other one.
```
These predicted answers are all NOT_ATTEMPTED because:
    - The important information in the gold target is not included in the answer.
    - No statements in the answer contradict the gold target.


Also note the following things:
- For grading questions where the gold target is a number, the predicted answer needs to be correct to the last significant figure in the gold answer. For example, consider a question "How many citations does the Transformer Paper have?" with gold target "120k". 
    - Predicted answers "120k", "124k", and 115k" are all CORRECT. 
    - Predicted answers "100k" and "113k" are INCORRECT. 
    - Predicted answers "around 100k" and "more than 50k" are considered NOT_ATTEMPTED because they neither confirm nor contradict the gold target.
- The gold target may contain more information than the question. In such cases, the predicted answer only needs to contain the information that is in the question.
    - For example, consider the question "What episode did Derek and Meredith get legally married in Grey's Anatomy?" with gold target "Season 7, Episode 20: White Wedding". Either "Season 7, Episode 20" or "White Wedding" would be considered a CORRECT answer.
- Do not punish predicted answers if they omit information that would be clearly inferred from the question.
    - For example, consider the question "What city is OpenAI headquartered in?" and the gold target "San Francisco, California". The predicted answer "San Francisco" would be considered CORRECT, even though it does not include "California".
    - Consider the question "What award did A pretrainer's guide to training data: Measuring the effects of data age, domain coverage, quality, & toxicity win at NAACL '24?", the gold target is "Outstanding Paper Award". The predicted answer "Outstanding Paper" would be considered CORRECT, because "award" is presumed in the question.
    - For the question "What is the height of Jason Wei in meters?", the gold target is "1.73 m". The predicted answer "1.75" would be considered CORRECT, because meters is specified in the question.
    - For the question "What is the name of Barack Obama's wife?", the gold target is "Michelle Obama". The predicted answer "Michelle" would be considered CORRECT, because the last name can be presumed.
- Do not punish for typos in people's name if it's clearly the same name. 
    - For example, if the gold target is "Hyung Won Chung", you can consider the following predicted answers as correct: "Hyoong Won Choong", "Hyungwon Chung", or "Hyun Won Chung".


Here is a new example. Simply reply with either CORRECT, INCORRECT, NOT ATTEMPTED. Don't apologize or correct yourself if there was a mistake; we are just trying to grade the answer.
```
Question: {}
Gold target: {}
Predicted answer: {}
```

Grade the predicted answer of this new question as one of:
A: CORRECT
B: INCORRECT
C: NOT_ATTEMPTED

Just return the letters "A", "B", or "C", with no text around it.
""".strip()
    
    @retry(
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS)
    )
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Use LLM to verify answer using SimpleQA evaluation protocol.
        
        Args:
            question: The question being answered
            target: Ground truth answer
            predicted_answer: Model's predicted answer
            metadata: Optional metadata (unused)
        
        Returns:
            "CORRECT", "INCORRECT", or "NOT_ATTEMPTED"
        
        Raises:
            Exception: If LLM response cannot be parsed
        """
        CHOICE_MAP = {
            "A": EVAL_CORRECT,
            "B": EVAL_INCORRECT,
            "C": EVAL_NOT_ATTEMPTED
        }
        
        messages = [
            {
                "role": "user",
                "content": self.EVALUATION_PROMPT.format(
                    question, target, predicted_answer
                ),
            }
        ]
        
        llm_response = await self.openai_client.chat.completions.create(
            model=LLM_GPT4O_MINI,
            messages=messages,
            max_completion_tokens=self.MAX_TOKENS,
            temperature=TEMP_DETERMINISTIC
        )
        
        content = llm_response.choices[0].message.content
        match = re.search(r"(A|B|C)", content)
        
        if match:
            return CHOICE_MAP[match.group(0)]
        else:
            raise Exception(f"SimpleQA LLM evaluation failed: {content}")

# ============================================================================
# XBench Verifier (Chinese)
# ============================================================================

class XBenchVerifier(BaseVerifier):
    """Verifier for XBench benchmark using LLM-based evaluation (Chinese)."""
    
    MAX_TOKENS = 4096
    
    JUDGE_PROMPT = """
你是一个通用人工智能助手。根据下面给出的[正确答案], 判断以下对[原问题]的[回答]的回答是否正确。

[原问题]: {question}

[正确答案]: {correct_answer}

[回答]:{response}

你的判断必须按照以下格式和标准进行:

最终答案: 从[回答]中提取出的最终准确答案。如果[回答]中没有明确的最终答案, 则填写'无'。

解释: 根据[原问题]解释为什么[最终答案]是正确的或错误的。只关注[最终答案]与[正确答案]之间是否存在实质性差异, 不要评论题目的背景, 不要尝试重新解题, 不要为任何不同于[正确答案]的答案辩护, 只专注于判断答案是否一致。

结论: 如果[最终答案]与上方给出的[正确答案]一致, 或者在数值题目中处于可接受的微小误差范围内, 则填写'正确'; 否则（即存在任何不一致、歧义、不等价或提取出的答案错误的情况）填写'错误'。
""".strip()
    
    class ExtractedAnswer(BaseModel):
        最终答案: str
        解释: str
        结论: Literal["正确", "错误"]
        strict: Literal[True] = True  # 100% reliability
    
    @retry(
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS)
    )
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Use XBench-style LLM judge to verify answer (Chinese evaluation).
        
        Args:
            question: The question being answered
            target: Ground truth answer
            predicted_answer: Model's predicted answer
            metadata: Optional metadata (unused)
        
        Returns:
            "CORRECT" or "INCORRECT"
        
        Raises:
            Exception: If evaluation fails or result cannot be parsed
        """
        prompt = self.JUDGE_PROMPT.format(
            question=question, correct_answer=target, response=predicted_answer
        )
        
        response = await self.openai_client.beta.chat.completions.parse(
            model=LLM_O3,  # TODO: Consider using deepseek-v3 as per XBench default
            max_completion_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            response_format=self.ExtractedAnswer,
        )
        
        content = response.choices[0].message.parsed
        
        # Print XBench reasoning
        print(f"XBench LLM Judge Extracted Answer: {content.最终答案}")
        print(f"XBench LLM Judge Reasoning: {content.解释}")
        print(f"XBench LLM Judge Result: {content.结论}")
        
        # Convert XBench format to standard format
        if content.结论 == "正确":
            return EVAL_CORRECT
        elif content.结论 == "错误":
            return EVAL_INCORRECT
        else:
            raise Exception(f"XBench LLM evaluation failed: {content}")


# ============================================================================
# HLE Verifier
# ============================================================================

class HLEVerifier(BaseVerifier):
    """Verifier for HLE and similar benchmarks using LLM-based evaluation."""
    
    MAX_TOKENS = 4096
    
    JUDGE_PROMPT = """Judge whether the following [response] to [question] is correct or not based on the precise and unambiguous [correct_answer] below.

[question]: {question}

[response]: {response}

Your judgement must be in the format and criteria specified below:

extracted_final_answer: The final exact answer extracted from the [response]. Put the extracted answer as 'None' if there is no exact, final answer to extract from the response.

[correct_answer]: {correct_answer}

reasoning: Explain why the extracted_final_answer is correct or incorrect based on [correct_answer], focusing only on if there are meaningful differences between [correct_answer] and the extracted_final_answer. Do not comment on any background to the problem, do not attempt to solve the problem, do not argue for any answer different than [correct_answer], focus only on whether the answers match.

correct: Answer 'yes' if extracted_final_answer matches the [correct_answer] given above, or is within a small margin of error for numerical problems. Answer 'no' otherwise, i.e. if there if there is any inconsistency, ambiguity, non-equivalency, or if the extracted answer is incorrect.

confidence: The extracted confidence score between 0|%| and 100|%| from [response]. Put 100 if there is no confidence score available."""
    
    class ExtractedAnswer(BaseModel):
        extracted_final_answer: str
        reasoning: str
        correct: Literal["yes", "no"]
        confidence: int
        strict: Literal[True] = True  # 100% reliability
    
    @retry(
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS)
    )
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Use HLE-style LLM judge to verify answer.
        
        Args:
            question: The question being answered
            target: Ground truth answer
            predicted_answer: Model's predicted answer
            metadata: Optional metadata (unused)
        
        Returns:
            "CORRECT" or "INCORRECT"
        
        Raises:
            Exception: If evaluation fails or result cannot be parsed
        """
        prompt = self.JUDGE_PROMPT.format(
            question=question, correct_answer=target, response=predicted_answer
        )
        
        response = await self.openai_client.beta.chat.completions.parse(
            model=LLM_O3_MINI,
            max_completion_tokens=self.MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
            response_format=self.ExtractedAnswer,
        )
        
        content = response.choices[0].message.parsed
        
        # Print HLE reasoning
        print(f"LLM as Judge Reasoning: {content.reasoning}")
        print(f"LLM as Judge Result: {content.correct}")
        print(f"LLM as Judge Confidence: {content.confidence}%")
        
        # Convert HLE format to standard format
        if content.correct == "yes":
            return EVAL_CORRECT
        elif content.correct == "no":
            return EVAL_INCORRECT
        else:
            raise Exception(f"HLE LLM evaluation failed: {content}")


# ============================================================================
# GAIA Verifier (Exact Matching with Normalization)
# ============================================================================

class GAIAVerifier(BaseVerifier):
    """Verifier for GAIA benchmark using exact matching with normalization."""
    
    def __init__(self, openai_client: Optional[AsyncOpenAI] = None):
        """GAIA verifier doesn't need OpenAI client."""
        super().__init__(openai_client)
    
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Use GAIA-style judge to verify answer (exact matching with normalization).
        
        Args:
            question: The question being answered (unused)
            target: Ground truth answer
            predicted_answer: Model's predicted answer
            metadata: Optional metadata (unused)
        
        Returns:
            "CORRECT" or "INCORRECT"
        
        Raises:
            Exception: If evaluation fails
        """
        try:
            is_correct = self._score_answer(predicted_answer, target)
            return EVAL_CORRECT if is_correct else EVAL_INCORRECT
        except Exception as e:
            print(f"GAIA evaluation failed: {e}")
            raise e
    
    @staticmethod
    def _normalize_number_str(number_str: str) -> float:
        """
        Normalize a number string by removing common units and commas.
        
        Args:
            number_str: String representation of a number
        
        Returns:
            Float value of the number, or inf if conversion fails
        """
        for char in ["$", "%", ","]:
            number_str = number_str.replace(char, "")
        try:
            return float(number_str)
        except ValueError:
            print(f"String {number_str} cannot be normalized to number str.")
            return float("inf")
    
    @staticmethod
    def _split_string(s: str, char_list: List[str] = None) -> List[str]:
        """
        Split string by multiple delimiters.
        
        Args:
            s: String to split
            char_list: List of delimiter characters (default: [",", ";"])
        
        Returns:
            List of split strings
        """
        if char_list is None:
            char_list = [",", ";"]
        pattern = f"[{''.join(char_list)}]"
        return re.split(pattern, s)
    
    @staticmethod
    def _normalize_str(input_str: str, remove_punct: bool = True) -> str:
        """
        Normalize a string by removing whitespace, punctuation, and converting to lowercase.
        
        Args:
            input_str: String to normalize
            remove_punct: Whether to remove punctuation (default: True)
        
        Returns:
            Normalized string
        """
        # Remove all whitespace (e.g., "sea gull" vs "seagull")
        no_spaces = re.sub(r"\s", "", input_str)
        
        if remove_punct:
            translator = str.maketrans("", "", string.punctuation)
            return no_spaces.lower().translate(translator)
        else:
            return no_spaces.lower()
    
    @staticmethod
    def _is_float(element: Any) -> bool:
        """Check if an element can be converted to float."""
        try:
            float(element)
            return True
        except ValueError:
            return False
    
    def _compare_as_number(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as numbers."""
        print(f"Evaluating {model_answer} as a number.")
        normalized_answer = self._normalize_number_str(model_answer)
        return normalized_answer == float(ground_truth)
    
    def _compare_as_list(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as comma/semicolon-separated lists."""
        print(f"Evaluating {model_answer} as a comma separated list.")
        
        gt_elems = self._split_string(ground_truth)
        ma_elems = self._split_string(model_answer)
        
        # Check if lengths match
        if len(gt_elems) != len(ma_elems):
            warnings.warn(
                "Answer lists have different lengths, returning False.",
                UserWarning
            )
            return False
        
        # Compare each element as float or string
        comparisons = []
        for ma_elem, gt_elem in zip(ma_elems, gt_elems):
            if self._is_float(gt_elem):
                normalized_ma_elem = self._normalize_number_str(ma_elem)
                comparisons.append(normalized_ma_elem == float(gt_elem))
            else:
                # Don't remove punctuation for list comparisons
                comparisons.append(
                    self._normalize_str(ma_elem, remove_punct=False)
                    == self._normalize_str(gt_elem, remove_punct=False)
                )
        
        return all(comparisons)
    
    def _compare_as_string(self, model_answer: str, ground_truth: str) -> bool:
        """Compare answers as strings."""
        print(f"Evaluating {model_answer} as a string.")
        return self._normalize_str(model_answer) == self._normalize_str(ground_truth)
    
    def _score_answer(self, model_answer: str, ground_truth: str) -> bool:
        """
        Score a model answer against ground truth using GAIA evaluation logic.
        
        Args:
            model_answer: Model's predicted answer
            ground_truth: Ground truth answer
        
        Returns:
            True if answers match, False otherwise
        """
        if model_answer is None:
            model_answer = "None"
        
        # Check if ground truth is a number
        if self._is_float(ground_truth):
            return self._compare_as_number(model_answer, ground_truth)
        
        # Check if ground truth is a list
        elif any(char in ground_truth for char in [",", ";"]):
            return self._compare_as_list(model_answer, ground_truth)
        
        # Otherwise, treat as string
        else:
            return self._compare_as_string(model_answer, ground_truth)


# ============================================================================
# FinSearchComp Verifier (Dynamic Judge Prompts)
# ============================================================================

class FinSearchCompVerifier(BaseVerifier):
    """Verifier for FinSearchComp benchmark using dynamic LLM judge prompts."""
    
    MAX_TOKENS = 2048
    
    @retry(
        wait=wait_exponential(multiplier=RETRY_MULTIPLIER),
        stop=stop_after_attempt(RETRY_MAX_ATTEMPTS)
    )
    async def verify(
        self,
        question: str,
        target: str,
        predicted_answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Use FinSearchComp-style LLM judge with dynamic prompts.
        
        Args:
            question: The question being answered
            target: The correct/target answer (primary ground truth)
            predicted_answer: The model's predicted answer
            metadata: Metadata containing judge_prompt_template, judge_system_prompt,
                      response_reference, and ground_truth_finance
        
        Returns:
            "CORRECT", "INCORRECT", or "NOT_ATTEMPTED"
        """
        if metadata is None:
            raise ValueError("FinSearchComp verifier requires metadata")
        
        # Extract judge prompts from metadata
        judge_prompt_template = metadata["judge_prompt_template"]
        judge_system_prompt = metadata["judge_system_prompt"]
        
        # Extract metadata fields
        response_reference = metadata.get("response_reference", "")
        ground_truth_finance = metadata.get("ground_truth_finance", "")
        
        # Format prompts
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
            
            # Parse response
            return self._parse_response(content)
        
        except Exception as e:
            print(f"FinSearchComp LLM evaluation failed: {e}")
            return EVAL_NOT_ATTEMPTED
    
    @staticmethod
    def _parse_response(content: str) -> str:
        """
        Parse FinSearchComp judge response to extract evaluation result.
        
        Args:
            content: Response content from the LLM judge
        
        Returns:
            "CORRECT", "INCORRECT", or "NOT_ATTEMPTED"
        """
        # Check for score patterns in the response
        score_patterns = [
            (r'"answer_score":\s*1', EVAL_CORRECT),
            (r'"answer_score":\s*0', EVAL_INCORRECT),
            (r'"score":\s*1', EVAL_CORRECT),
            (r'"score":\s*0', EVAL_INCORRECT),
        ]
        
        for pattern, result in score_patterns:
            if re.search(pattern, content):
                return result
        
        # Could not parse response
        print(f"Warning: Could not parse FinSearchComp judge response: {content}")
        return EVAL_NOT_ATTEMPTED
