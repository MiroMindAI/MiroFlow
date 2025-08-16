#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0


import asyncio
import glob
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple

import dotenv
from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
from tenacity import stop_after_attempt, wait_exponential
from tenacity.asyncio import AsyncRetrying

from eval_utils import verify_answer_gaia
from miroflow.utils.io_utils import OutputFormatter

# Constants
DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MAX_RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN = 1  # seconds
RETRY_WAIT_MAX = 10  # seconds
MAX_CONCURRENT_REQUESTS = 5  # Maximum concurrent API requests
SEMAPHORE_TIMEOUT = 300  # Timeout for acquiring semaphore in seconds
VERBOSE = False

dotenv.load_dotenv()


def extract_from_log(
    run_dir: str, task_score_dict: Dict[str, List[Dict[str, Any]]]
) -> None:
    """Extract task data from log files in a run directory."""
    try:
        log_files = glob.glob(os.path.join(run_dir, "*attempt*"))
        for log_file in log_files:
            try:
                task_id = log_file.split("/")[-1].split("_")[0]
                with open(log_file, "r") as f:
                    data = json.load(f)
                    if task_id not in task_score_dict:
                        task_score_dict[task_id] = []
                    task_score_dict[task_id].append(
                        # select some keys from data
                        {
                            "task_id": data["task_id"],
                            "task_name": data["task_name"],
                            "ground_truth": data["ground_truth"],
                            "final_boxed_answer": data["final_boxed_answer"],
                            "input": data["input"],
                            "main_agent_message_history": data[
                                "main_agent_message_history"
                            ],
                        }
                    )
            except (json.JSONDecodeError, KeyError, IOError) as e:
                print(f"Warning: Could not process log file {log_file}: {e}")
                continue
    except Exception as e:
        print(f"Error processing run directory {run_dir}: {e}")
        raise


async def select_best_solution(
    prompt: str,
    n_runs: int,
    model: str = DEFAULT_MODEL,
    semaphore: Optional[asyncio.Semaphore] = None,
) -> str:
    """Select the best solution using LLM with retry logic and concurrency control."""

    async def _make_api_call():
        """Make the actual API call with proper error handling."""
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable not set")

        client = AsyncOpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=api_key,
        )

        completion = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
        )

        response = completion.choices[0].message.content
        if not response:
            raise ValueError("Empty response from API")

        return response

    # Use semaphore for concurrency control if provided
    if semaphore:
        async with semaphore:
            return await _retry_api_call(_make_api_call)
    else:
        return await _retry_api_call(_make_api_call)


async def _retry_api_call(api_call_func):
    """Retry logic for API calls using AsyncRetrying."""
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(MAX_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=1, min=RETRY_WAIT_MIN, max=RETRY_WAIT_MAX),
        reraise=True,
    ):
        with attempt:
            try:
                return await api_call_func()
            except (
                APIError,
                APIConnectionError,
                RateLimitError,
                APITimeoutError,
                ConnectionError,
            ) as e:
                print(
                    f"Retryable API error (attempt {attempt.retry_state.attempt_number}): {e}"
                )
                raise  # Let tenacity handle the retry
            except Exception as e:
                print(f"Non-retryable error in select_best_solution: {e}")
                raise


def load_task_data(results_dir: str) -> Dict[str, List[Dict[str, Any]]]:
    """Load task data from all run directories."""
    run_dirs = glob.glob(os.path.join(results_dir, "run_*"))
    run_dirs = [d for d in run_dirs if os.path.isdir(d)]

    task_score_dict: Dict[str, List[Dict[str, Any]]] = {}
    for run_dir in run_dirs:
        extract_from_log(run_dir, task_score_dict)

    return task_score_dict


def create_selection_prompt(task_data: List[Dict[str, Any]], n_runs: int) -> str:
    """Create prompt for solution selection."""
#     prompt = f"""You are an expert evaluator. Your task is to analyze multiple answers to a question and determine the final answer based on majority vote.

# Question: 
# {task_data[0]["input"]}

# Refer to the following {n_runs} solutions and select the best solution. Make sure the answer is in `\\boxed{{}}`.
#     """
    # answers_text = ";".join([d["final_boxed_answer"] for d in task_data])
    answers_text = [f"{d['final_boxed_answer']}" for d in task_data]
    prompt= f"""You are an expert evaluator. Your task is to analyze multiple answers to a question and determine the final answer based on majority vote.

Question: {task_data[0]["input"]}

Multiple Answers:
{answers_text}

Instructions:
1. Review all the provided answers carefully
2. Identify the answer that appears most frequently among all the responses (majority vote)
3. If there's a tie, choose any of the most frequent answers (or apply a tie-breaking rule if provided)
4. You must strictly select the final answer from the provided answers only — do NOT generate or infer any new answers
5. Return ONLY the final answer in the exact format expected (e.g., "A", "B", "C", "D" for multiple choice, or the exact text for other formats)
6. Your final answer should be wrapped in \\boxed{{...}}

Final Answer:
"""
#     for i, d in enumerate(task_data):
#         prompt += f"""
# {'-'*100}
# Solution {i+1}:
# {d["main_agent_message_history"]["message_history"][-2]["content"]}
# {d["main_agent_message_history"]["message_history"][-1]["content"][0]["text"]}
# """
    return prompt


async def process_single_task(
    task_id: str, data: List[Dict[str, Any]], n_runs: int, semaphore: asyncio.Semaphore
) -> Tuple[str, Dict[str, Any]]:
    """Process a single task and return its result."""
    formatter = OutputFormatter()

    prompt = create_selection_prompt(data, n_runs)
    response = await select_best_solution(prompt, n_runs, semaphore=semaphore)
    selected_solution = formatter._extract_boxed_content(response)
    result = await verify_answer_gaia(data[0]["ground_truth"], selected_solution)

    task_result = {
        "task_id": task_id,
        "candidate_answers": [d["final_boxed_answer"] for d in data],
        "ground_truth": data[0]["ground_truth"],
        "input": prompt,
        "selected_solution": selected_solution,
        "selected_solution_result": result,
        "selected_solution_reasoning": response,
    }

    return task_id, task_result


async def process_tasks(
    task_score_dict: Dict[str, List[Dict[str, Any]]],
    n_runs: int,
    max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS,
) -> Dict[str, Dict[str, Any]]:
    """Process all tasks concurrently and select best solutions."""
    # Create semaphore for rate limiting
    semaphore = asyncio.Semaphore(max_concurrent_requests)

    # Create tasks for concurrent execution
    tasks = [
        process_single_task(task_id, data, n_runs, semaphore)
        for task_id, data in task_score_dict.items()
    ]

    total_tasks = len(tasks)
    print(
        f"Processing {total_tasks} tasks concurrently (max {max_concurrent_requests} concurrent requests)..."
    )

    # Process tasks and show progress as they complete
    task_results: Dict[str, Dict[str, Any]] = {}
    completed_tasks = 0

    for coro in asyncio.as_completed(tasks):
        try:
            result = await coro
            task_id, task_result = result
            task_results[task_id] = task_result
            completed_tasks += 1

            # Show progress indicator
            progress_percent = (completed_tasks / total_tasks) * 100
            if VERBOSE:
                print(
                    f"Progress: {completed_tasks}/{total_tasks} ({progress_percent:.1f}%) - Completed task: {task_id}"
                )

        except Exception as e:
            completed_tasks += 1
            progress_percent = (completed_tasks / total_tasks) * 100
            if VERBOSE:
                print(
                    f"Progress: {completed_tasks}/{total_tasks} ({progress_percent:.1f}%) - Error processing task: {e}"
                )
            # Continue with other tasks instead of failing completely
            continue

    print(f"Successfully processed {len(task_results)} out of {total_tasks} tasks")
    return task_results


def save_results(
    results_dir: str, task_results: Dict[str, Dict[str, Any]], n_runs: int
) -> None:
    """Save results to files."""
    try:
        # Save detailed results
        results_file = os.path.join(
            results_dir, f"llm_majority_voter_{n_runs}runs.json"
        )
        with open(results_file, "w") as f:
            json.dump(task_results, f, indent=4)

        # Calculate and save accuracy
        correct_count = sum(
            1
            for data in task_results.values()
            if data["selected_solution_result"] == "CORRECT"
        )
        accuracy = correct_count / len(task_results) if task_results else 0.0

        print(f"Accuracy: {accuracy}")

        accuracy_file = os.path.join(
            results_dir, f"llm_majority_voter_accuracy_{n_runs}runs.txt"
        )
        with open(accuracy_file, "w") as f:
            f.write(f"Accuracy: {accuracy}")

    except IOError as e:
        print(f"Error saving results: {e}")
        raise


async def main(
    results_dir: str, max_concurrent_requests: int = MAX_CONCURRENT_REQUESTS
) -> None:
    """Main function to analyze results and select best solutions."""
    if not os.path.exists(results_dir):
        print(f"Results directory does not exist: {results_dir}")
        sys.exit(1)

    print(f"Analyzing results from: {results_dir}")

    # Load task data from all runs
    task_score_dict = load_task_data(results_dir)
    if not task_score_dict:
        print("No task data found")
        return

    # Get number of runs
    run_dirs = glob.glob(os.path.join(results_dir, "run_*"))
    n_runs = len([d for d in run_dirs if os.path.isdir(d)])

    # Process all tasks
    task_results = await process_tasks(task_score_dict, n_runs, max_concurrent_requests)

    # Save results
    save_results(results_dir, task_results, n_runs)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python select.py <results_dir> [max_concurrent_requests]")
        sys.exit(1)

    results_dir = sys.argv[1]
    max_concurrent_requests = MAX_CONCURRENT_REQUESTS

    if len(sys.argv) >= 3:
        try:
            max_concurrent_requests = int(sys.argv[2])
            if max_concurrent_requests <= 0:
                print("Error: max_concurrent_requests must be a positive integer")
                sys.exit(1)
        except ValueError:
            print("Error: max_concurrent_requests must be a valid integer")
            sys.exit(1)

    asyncio.run(main(results_dir, max_concurrent_requests))
