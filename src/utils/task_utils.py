# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import json
import os
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

from src.logging.task_tracer import TaskTracer, set_current_tracer, reset_current_tracer


# ============================================================================
# Types and Data Classes
# ============================================================================

class TaskStatus(StrEnum):
    PENDING = "pending"
    RUN_FAILED = "run_failed"
    RUN_COMPLETED = "run_completed"
    RESULT_JUDGED = "result_judged"


class AttemptStats(TypedDict):
    attempt_number: int
    model_response: str
    model_boxed_answer: str
    status: TaskStatus
    log_file_path: Optional[Path]
    judge_result: Optional[str]
    is_correct: bool
    error_message: Optional[str]


def update_attempt_stats(
    attempt_result: AttemptStats,
    response: Dict[str, Any],
    log_path: Path,
    tracer: Any,  # TaskTracer type, but avoiding circular import
) -> AttemptStats:
    """
    Update AttemptStats with response data.
    
    Args:
        attempt_result: AttemptStats dictionary to update
        response: Response dictionary from agent.run()
        log_path: Path to the log file
        tracer: TaskTracer instance
        
    Returns:
        Updated AttemptStats dictionary
    """
    final_boxed_answer = response.get('final_boxed_answer', '')
    tracer.update_task_meta(patch={
        'final_boxed_answer': final_boxed_answer
    })
    
    attempt_result["log_file_path"] = log_path
    if final_boxed_answer:
        attempt_result["model_boxed_answer"] = final_boxed_answer
        attempt_result["status"] = TaskStatus.RUN_COMPLETED
    else:
        attempt_result["model_boxed_answer"] = final_boxed_answer
        attempt_result["status"] = TaskStatus.RUN_FAILED
    
    return attempt_result


async def run_single_task_attempt(
    attempt_result: AttemptStats,
    evaluator_output_dir: Path,
    task_id: str,
    attempt: int,
    task_description: str,
    task_file_path: str,
    agent: Any,  # BaseAgentModule type, but avoiding circular import
) -> AttemptStats:
    """
    Execute a single task attempt.
    
    This function wraps the logic for running a single attempt of a task,
    including tracer setup, agent execution, stats update, and cleanup.
    
    Args:
        attempt_result: AttemptStats dictionary to update
        evaluator_output_dir: Output directory for logs
        task_id: Task identifier
        attempt: Attempt number (1-indexed)
        task_description: Task description string
        task_file_path: Path to task file (if any)
        agent: Agent instance for running tasks
        
    Returns:
        Updated AttemptStats dictionary
    """
    log_path = evaluator_output_dir / f"task_{task_id}_attempt_{attempt}.json"
    tracer = TaskTracer(log_path=log_path)
    token = set_current_tracer(tracer)
    
    try:
        response = await agent.run(
            dict(
                task_description=task_description,
                task_file_name=task_file_path
            )
        )
        
        attempt_result = update_attempt_stats(
            attempt_result, response, log_path, tracer
        )

    except Exception as e:
        attempt_result["status"] = TaskStatus.RUN_FAILED
        attempt_result["error_message"] = str(e)
        print(f"    Error in attempt {attempt}: {e}")

    finally:
        reset_current_tracer(token)
        tracer.finish(status="completed")
    
    return attempt_result


# ============================================================================
# Attempt Management Functions
# ============================================================================

def scan_latest_attempt(
    evaluator: Any,  # BenchmarkEvaluator type, but avoiding circular import
    task: Any,  # BenchmarkTask type, but avoiding circular import
    attempt: int
) -> AttemptStats:
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
    matched_logs = evaluator.output_dir.glob(trace_filename_pattern)
    sorted_logs = sorted(matched_logs, reverse=True)
    if len(sorted_logs) == 0:
        return attempt_result
    latest_log = sorted_logs[-1]
    attempt_result["status"] = TaskStatus.RUN_FAILED
    attempt_result["log_file_path"] = latest_log
    print(f"    Found existing log for attempt {attempt}: {latest_log.name}")

    with open(latest_log) as f:
        log_data = json.loads(f.read())
        final_boxed_answer = log_data.get("task_meta", {}).get("final_boxed_answer", "")
        if final_boxed_answer:
            attempt_result["status"] = TaskStatus.RUN_COMPLETED
            attempt_result["model_boxed_answer"] = final_boxed_answer
            attempt_result["model_response"] = log_data.get("output", "")
            # Check if we already have LLM judge result in log
            judge_result = log_data.get("task_meta", {}).get("judge_result", "")
            if judge_result:
                attempt_result["status"] = TaskStatus.RESULT_JUDGED
                attempt_result["judge_result"] = judge_result
                attempt_result["is_correct"] = judge_result == "CORRECT"
            print(
                f"    Loaded existing result: {attempt_result['model_boxed_answer']}"
            )
    return attempt_result


async def update_log_file_with_evaluation(
    log_file_path: Path, evaluation_result: str
):
    """Helper method to update log file with evaluation result"""
    try:
        log_file = Path(log_file_path)
        # Read existing data
        with open(log_file, "r", encoding="utf-8") as f:
            log_data = json.load(f)

        # Update with evaluation result in task_meta
        if "task_meta" not in log_data:
            log_data["task_meta"] = {}
        log_data["task_meta"]["judge_result"] = evaluation_result

        # Write to a temporary file and then atomically replace
        temp_log_file = log_file.with_suffix(f"{log_file.suffix}.tmp")
        with open(temp_log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, ensure_ascii=False)

        os.replace(temp_log_file, log_file)
        print(f"    Updated log file {log_file.name} with evaluation result.")
    except Exception as e:
        print(f"    Error updating log file {log_file_path}: {e}")


async def run_single_attempt(
    evaluator: Any,  # BenchmarkEvaluator type, but avoiding circular import
    task: Any,  # BenchmarkTask type, but avoiding circular import
    attempt: int,
    task_description: str,
    task_file_path: Optional[str],
    agent: Any,  # BaseAgentModule type, but avoiding circular import
) -> AttemptStats:
    """
    Run a single attempt for a task.
    
    Args:
        evaluator: BenchmarkEvaluator instance
        task: BenchmarkTask object
        attempt: Attempt number (1-indexed)
        task_description: Prepared task description
        task_file_path: Optional file path for the task
        agent: Agent instance for running tasks
        
    Returns:
        AttemptStats dictionary with attempt results
    """
    # Check for existing attempt result
    attempt_result = scan_latest_attempt(evaluator, task, attempt)
    
    # Run inference if no existing result or previous attempt failed
    if attempt_result["status"] in (TaskStatus.PENDING, TaskStatus.RUN_FAILED):
        log_path = evaluator.output_dir / f"task_{task.task_id}_attempt_{attempt}.json"
        tracer = TaskTracer(log_path=log_path)
        token = set_current_tracer(tracer)
        
        try:
            response = await agent.run(
                dict(
                    task_description=task_description,
                    task_file_name=task_file_path
                )
            )
            
            final_boxed_answer = response.get('final_boxed_answer', '')
            tracer.update_task_meta(patch={
                'final_boxed_answer': final_boxed_answer
            })
            
            attempt_result["log_file_path"] = log_path
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
            
        finally:
            reset_current_tracer(token)
            tracer.finish(status="completed")
    
    return attempt_result


async def verify_attempt_result(
    evaluator: Any,  # BenchmarkEvaluator type, but avoiding circular import
    task: Any,  # BenchmarkTask type, but avoiding circular import
    attempt: int,
    attempt_result: AttemptStats,
) -> AttemptStats:
    """
    Verify a single attempt result using LLM judge.
    
    This function assumes the attempt has RUN_COMPLETED status.
    Caller should check the status before calling this function.
    
    Args:
        evaluator: BenchmarkEvaluator instance
        task: BenchmarkTask object
        attempt: Attempt number (1-indexed)
        attempt_result: AttemptStats dictionary to verify
        
    Returns:
        Updated AttemptStats dictionary with verification results
    """
    from src.utils.eval_utils import verify_answer_for_datasets
    
    # Perform LLM verification if we have an answer and haven't verified yet
    if attempt_result.get("judge_result") is None:
        print(f"    Verifying answer for attempt {attempt}...")
        try:
            evaluation_result = await verify_answer_for_datasets(
                openai_client=evaluator.evaluation_llm,
                benchmark_name=evaluator.benchmark_name,
                question=task.task_question,
                target=task.ground_truth,
                predicted_answer=attempt_result["model_boxed_answer"],
                metadata=task.metadata,
            )
            attempt_result["judge_result"] = evaluation_result
            attempt_result["is_correct"] = evaluation_result == "CORRECT"
            
            # Update the log file with verification result
            if attempt_result.get("log_file_path"):
                await update_log_file_with_evaluation(
                    attempt_result["log_file_path"], evaluation_result
                )
            
            if attempt_result["is_correct"]:
                print(f"    ✅ Attempt {attempt}: CORRECT!")
            else:
                print(f"    ❌ Attempt {attempt}: INCORRECT ({evaluation_result})")
                
        except Exception as e:
            print(f"    Error verifying attempt {attempt}: {e}")
            attempt_result["judge_result"] = "ERROR"
            attempt_result["is_correct"] = False
    else:
        # Already verified
        if attempt_result["is_correct"]:
            print(f"    ✅ Attempt {attempt}: CORRECT (cached)")
        else:
            print(f"    ❌ Attempt {attempt}: INCORRECT (cached: {attempt_result['judge_result']})")
    
    return attempt_result


def update_result_with_attempt(
    result: Any,  # BenchmarkResult type, but avoiding circular import
    attempt_result: AttemptStats,
    attempt: int,
) -> None:
    """
    Update BenchmarkResult with attempt result.
    
    This function:
    1. Appends the attempt_result to result.attempts
    2. Updates main result fields with the first attempt or when we get a successful completion
    
    Args:
        result: BenchmarkResult object to update
        attempt_result: AttemptStats dictionary with attempt results
        attempt: Attempt number (1-indexed)
    """
    result.attempts.append(attempt_result)
    
    # Update main result with the first successful attempt or best attempt so far
    if attempt == 1 or (not result.model_boxed_answer and attempt_result["status"] == TaskStatus.RUN_COMPLETED):
        result.model_response = attempt_result["model_response"]
        result.model_boxed_answer = attempt_result["model_boxed_answer"]
        result.log_file_path = attempt_result["log_file_path"]
        result.status = attempt_result["status"]
        result.error_message = attempt_result["error_message"]

