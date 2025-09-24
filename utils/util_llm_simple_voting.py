# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0


import asyncio
import glob
import json
import os
import sys
from typing import Dict, List, Any, Optional, Tuple, Literal

from openai import AsyncOpenAI
from openai import APIError, APIConnectionError, RateLimitError, APITimeoutError
from pydantic import BaseModel
from tenacity import stop_after_attempt, wait_exponential
from tenacity.asyncio import AsyncRetrying

from eval_utils import verify_answer_for_datasets
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")


class ExtractedAnswer(BaseModel):
    reasoning: str
    final_answer: str
    strict: Literal[True] = True  # 100% reliability


# Constants
BENCHMARK_NAME = "gaia-validation"  # Benchmark name for evaluation
RESULTS_DIRS = ["<your_results_dirs>"]

DEFAULT_MODEL = "o3"
OPENAI_BASE_URL = "https://api.openai.com/v1"
MAX_RETRY_ATTEMPTS = 3
RETRY_WAIT_MIN = 1  # seconds
RETRY_WAIT_MAX = 10  # seconds
MAX_CONCURRENT_REQUESTS = 25  # Maximum concurrent API requests
SEMAPHORE_TIMEOUT = 300  # Timeout for acquiring semaphore in seconds
VERBOSE = True


def process_message_history(main_agent_message_history: Dict[str, Any]) -> str:
    """Process and concatenate message history content."""
    try:
        message_history = main_agent_message_history["message_history"]

        # Process the second-to-last message content
        # preliminary_content = message_history[-2]["content"]
        # preliminary_content = preliminary_content.replace("## Final Answer", "## Preliminary Answer")

        # Process the last message content
        final_content = message_history[-1]["content"][0]["text"]
        final_content = final_content.replace(
            "O3 extracted final answer:", "## Final Answer Reasoning\n"
        )

        # Concatenate the two parts
        # combined_content = preliminary_content + "\n\n" + final_content
        combined_content = final_content
        return combined_content

    except (KeyError, IndexError, TypeError) as e:
        print(f"Warning: Could not process message history: {e}")
        return ""


def extract_from_log(
    run_dir: str, task_score_dict: Dict[str, List[Dict[str, Any]]]
) -> None:
    """Extract task data from log files in a run directory."""
    try:
        log_files = glob.glob(os.path.join(run_dir, "*attempt*"))
        for log_file in log_files:
            try:
                task_id = log_file.split("/")[-1].split("_")[1]
                with open(log_file, "r") as f:
                    data = json.load(f)
                    if task_id not in task_score_dict:
                        task_score_dict[task_id] = []
                    task_score_dict[task_id].append(
                        # select some keys from data
                        {
                            "task_id": data["task_id"],
                            "task_name": data["task_original_name"],
                            "ground_truth": data["ground_truth"],
                            "final_boxed_answer": data["final_boxed_answer"],
                            "input": data["input"],
                            "agent_summary": process_message_history(
                                data["main_agent_message_history"]
                            ),
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
        api_key = OPENAI_API_KEY

        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        client = AsyncOpenAI(
            base_url=OPENAI_BASE_URL,
            api_key=api_key,
        )

        completion = await client.beta.chat.completions.parse(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                    ],
                }
            ],
            response_format=ExtractedAnswer,
        )

        response = completion.choices[0].message.content
        if not response:
            raise ValueError("Empty response from API")

        # Parse the structured response
        parsed_response = json.loads(response)
        return parsed_response

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


def load_combined_task_data(
    results_dirs: List[str],
) -> Tuple[Dict[str, List[Dict[str, Any]]], int]:
    """Load and combine task data from multiple result directories."""
    combined_dict: Dict[str, List[Dict[str, Any]]] = {}
    total_runs = 0

    for results_dir in results_dirs:
        if not os.path.exists(results_dir):
            print(f"Warning: Skipping non-existent directory: {results_dir}")
            continue
        task_data = load_task_data(results_dir)
        run_count = len(
            [
                d
                for d in os.listdir(results_dir)
                if os.path.isdir(os.path.join(results_dir, d)) and d.startswith("run_")
            ]
        )
        total_runs += run_count

        for task_id, data_list in task_data.items():
            if task_id not in combined_dict:
                combined_dict[task_id] = []
            combined_dict[task_id].extend(data_list)

    return combined_dict, total_runs


def create_selection_gaia_prompt(task_data: List[Dict[str, Any]], n_runs: int) -> str:
    """Create prompt for solution selection."""
    #     prompt = f"""You are an expert evaluator. Your task is to analyze multiple answers to a question and determine the final answer based on majority vote.

    # Question:
    # {task_data[0]["input"]}

    # Refer to the following {n_runs} solutions and select the best solution. Make sure the answer is in `\\boxed{{}}`.
    #     """
    # answers_text = ";".join([d["final_boxed_answer"] for d in task_data])
    answers_text = [f"{d['final_boxed_answer']}" for d in task_data]
    prompt = f"""You are an expert evaluator working with me to determine the best answer from multiple responses. I need your help to identify which answers are equivalent and then select the most frequently occurring one.

Question: {task_data[0]["input"]}

Multiple Answers:
{answers_text}

Here's how we can approach this together:

**Understanding Equivalence:**
I'd like you to group answers that are equivalent according to these precise normalization rules:

For numerical answers:
   - Remove symbols "$", "%", and "," then convert to float numbers and compare
   - Examples: "1.5" equals "1.50", "$1,000" equals "1000", "50%" equals "50"
   - Must be exactly equal as float numbers after normalization

For text answers (single text, not lists):
   - Remove all spaces and punctuation, convert to lowercase, then compare
   - Examples: "sea gull" equals "seagull", "New York!" equals "newyork"
   - Note: "NYC" ≠ "New York City" (becomes "nyc" vs "newyorkcity" - different words)

For list answers (containing commas or semicolons):
   - Split into elements, lists must have same length
   - Compare elements in the same position
   - For each element: if it's a number, use number rules; if text, remove spaces only (keep punctuation), convert to lowercase
   - All corresponding elements must match
   - [Rule]: Questions shouldn't require pure numerical lists with >10 elements. If you see long numerical lists, the question likely expects a single number (e.g., sum, conversion). Interpret based on question intent and convert list to a single number before comparing equivalence.

**Important:** Valid answers always exist for these questions. Ignore responses containing "none", "not found", or similar expressions indicating no answer exists.

**Your Task:**
Please analyze these answers thoughtfully and:
1. Group the answers that you determine are equivalent
2. Identify which group appears most frequently 
3. Select the clearest representative answer from the winning group
4. Choose only from the original answers provided

I trust your judgment in applying these guidelines sensibly, especially for any edge cases that might arise.

Please respond in JSON format:
{{
    "reasoning": "Your analysis of how you grouped the answers and determined the majority",
    "final_answer": "Your selected answer (exactly as it appears in the original list)"
}}
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
    if "gaia" in BENCHMARK_NAME:
        prompt = create_selection_gaia_prompt(data, n_runs)
    else:
        raise ValueError(f"Unsupported benchmark name: {BENCHMARK_NAME}")

    response = await select_best_solution(prompt, n_runs, semaphore=semaphore)
    selected_solution = response["final_answer"]
    reasoning = response["reasoning"]
    result = await verify_answer_for_datasets(
        None, BENCHMARK_NAME, "", data[0]["ground_truth"], selected_solution, {}
    )

    task_result = {
        "task_id": task_id,
        "candidate_answers": [d["final_boxed_answer"] for d in data],
        "task_input": data[0]["input"],
        "prompt_input": prompt,
        "ground_truth": data[0]["ground_truth"],
        "selected_solution": selected_solution,
        "selected_solution_result": result,
        "selected_solution_reasoning": reasoning,
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
            json.dump(task_results, f, ensure_ascii=False, indent=4)

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
    max_concurrent_requests = MAX_CONCURRENT_REQUESTS

    # Use single or multiple directory mode based on whether results_dirs is defined above
    results_dirs = RESULTS_DIRS

    if results_dirs:
        # Multiple directories mode
        combined_dict, total_runs = load_combined_task_data(results_dirs)
        if not combined_dict:
            print("No task data found")
            sys.exit(1)
        print(
            f"Loaded {len(combined_dict)} tasks with {total_runs} total runs from {len(results_dirs)} directories"
        )

        async def main_combined():
            task_results = await process_tasks(
                combined_dict, total_runs, max_concurrent_requests
            )
            save_results(os.path.dirname(results_dirs[0]), task_results, total_runs)

        asyncio.run(main_combined())
    else:
        # Single directory mode
        # asyncio.run(main(results_dir, max_concurrent_requests))
        pass
