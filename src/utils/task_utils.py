# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Task execution utilities for benchmark evaluation.

This module provides functions for running single and multiple benchmark tasks,
including support for pass@k evaluation with early stopping.
"""

import asyncio
import random
from pathlib import Path
from typing import List

from omegaconf import DictConfig

from src.agents.base_module import BaseAgentModule
from src.logging.task_tracer import (
    TaskContextVar,
    get_tracer,
    reset_current_task_context_var,
    set_current_task_context_var,
)
from src.utils.eval_utils import (
    AttemptStats,
    BenchmarkEvaluator,
    BenchmarkResult,
    BenchmarkTask,
    TaskStatus,
)
tracer = get_tracer()

async def run_single_attempt(
    agent: BaseAgentModule,
    output_dir: Path,
    task_id: str,
    attempt_id: int,
    task_description: str,
    task_file_path: str,
    # 新增参数：控制是否在内部管理生命周期，默认为 False 以便被 run_single_task 调用
    manage_lifecycle: bool = False, 
) -> AttemptStats:
    
    attempt_result = AttemptStats(
        task_id=task_id,
        attempt_id=attempt_id,
        output_dir=output_dir,
    )
    if attempt_result["status"] not in (TaskStatus.PENDING, TaskStatus.RUN_FAILED):
        return attempt_result

    log_path = output_dir / f"task_{task_id}_attempt_{attempt_id}.json"
    
    token = None
    if manage_lifecycle:
        task_context_var = TaskContextVar(task_id=task_id, run_id=attempt_id)
        token = set_current_task_context_var(task_context_var)
        get_tracer().start()

    get_tracer().update_task_meta(
        patch={
            "task_id": task_id,
            "run_id": attempt_id,
            "task_description": task_description,
            "task_file_name": task_file_path,
        }
    )

    try:
        print(task_description)
        response = await agent.run(
            {
                "task_description": task_description,
                "task_file_name": task_file_path,
            }
        )
        attempt_result.update_from_response(response, log_path)

    except Exception as e:
        attempt_result["status"] = TaskStatus.RUN_FAILED
        attempt_result["error_message"] = str(e)
        print(f"    Error in attempt {attempt_id}: {e}")
        if manage_lifecycle:
            get_tracer().finish(status="failed", error=str(e))

    finally:
        if manage_lifecycle:
            get_tracer().finish(status="completed") 
            if token:
                reset_current_task_context_var(token)

    return attempt_result


# ============================================================================
# Task Execution Functions
# ============================================================================

async def run_single_task(
    agent: BaseAgentModule,
    cfg: DictConfig,
    evaluator: BenchmarkEvaluator,
    task: BenchmarkTask,
) -> BenchmarkResult:
    
    output_dir = Path(cfg.output_dir)
    print(f"Processing task {task.task_id} with pass@{evaluator.pass_at_k}")
    result = BenchmarkResult(cfg=cfg.benchmark, task=task)
    found_correct_answer = False

    try:
        task_description, task_file_path = evaluator.prepare_task_description(task)

        for attempt_id in range(1, evaluator.pass_at_k + 1):
            print(f"  Attempt {attempt_id}/{evaluator.pass_at_k} for task {task.task_id}")

            task_ctx = TaskContextVar(task_id=task.task_id, run_id=attempt_id)
            token = set_current_task_context_var(task_ctx)
            
            tracer.start() 

            try:
                attempt_result = await run_single_attempt(
                    agent=agent,
                    output_dir=output_dir,
                    task_id=task.task_id,
                    attempt_id=attempt_id,
                    task_description=task_description,
                    task_file_path=task_file_path,
                    manage_lifecycle=False, # <--- 关键：禁止内部 Finish
                )

                attempt_result = await evaluator.verify_attempt_result(
                    task, attempt_id, attempt_result
                )

                tracer.update_task_meta(patch={
                    'model_response': attempt_result.model_response,
                    'final_boxed_answer': attempt_result.model_boxed_answer,
                    'status': attempt_result.status,
                    'error': attempt_result.error_message,
                    'judge_result': attempt_result.judge_result,
                    'ground_truth': task.ground_truth
                })
                
                result.update_with_attempt(attempt_result)
                found_correct_answer = attempt_result.get("is_correct", False)

            except Exception as e:
                print(f"Error in loop attempt {attempt_id}: {e}")
                tracer.error(f"Attempt failed: {e}")
                tracer.finish(status="failed", error=str(e))
            else:
                tracer.finish(status="completed")
            finally:
                reset_current_task_context_var(token)
            

            if found_correct_answer:
                print(f"    🎯 Found correct answer! Stopping early.")
                break

    except Exception as e:
        result.error_message = str(e)
        result.status = "failed"
        print(f"Error processing task {task.task_id}: {e}")

    finally:
        result.pass_at_k_success = found_correct_answer
        if found_correct_answer:
            result.judge_result = "PASS_AT_K_SUCCESS"
        else:
            result.judge_result = "PASS_AT_K_FAILED"

        print(f"Task {task.task_id} completed.")
        
    return result

async def run_tasks(
    agent: BaseAgentModule,
    cfg: DictConfig,
    evaluator: BenchmarkEvaluator,
    tasks: List[BenchmarkTask],
    max_concurrent: int = 3,
) -> List[BenchmarkResult]:
    """Run inference on multiple tasks in parallel.

    Executes multiple benchmark tasks concurrently with a semaphore to limit
    the number of concurrent executions. Tasks are shuffled to avoid order bias
    and improve load balancing.

    Args:
        agent: Agent instance for running tasks.
        cfg: DictConfig object containing configuration.
        evaluator: BenchmarkEvaluator instance for task preparation and verification.
        tasks: List of BenchmarkTask objects to execute.
        max_concurrent: Maximum number of concurrent task executions. Defaults to 3.

    Returns:
        List of BenchmarkResult objects, one for each task. Tasks that raise
        exceptions are converted to failed BenchmarkResult objects.
    """
    print(f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent}")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(task: BenchmarkTask) -> BenchmarkResult:
        """Run a single task with semaphore control."""
        async with semaphore:
            return await run_single_task(
                agent=agent,
                cfg=cfg,
                evaluator=evaluator,
                task=task,
            )

    # Shuffle tasks to avoid order bias and improve load balancing
    shuffled_tasks = tasks.copy()
    random.shuffle(shuffled_tasks)

    # Run tasks in parallel
    results = await asyncio.gather(
        *[run_with_semaphore(task) for task in shuffled_tasks],
        return_exceptions=True,
    )

    # Convert exceptions to failed BenchmarkResult objects
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            print(f"Exception in task {shuffled_tasks[i].task_id}: {result}")
            error_task = BenchmarkTask(
                task_id=shuffled_tasks[i].task_id,
                task_question=shuffled_tasks[i].task_question,
                ground_truth=shuffled_tasks[i].ground_truth,
                file_path=shuffled_tasks[i].file_path,
                metadata=shuffled_tasks[i].metadata.copy(),
            )
            error_result = BenchmarkResult(cfg=cfg.benchmark, task=error_task)
            error_result.status = "failed"
            error_result.error_message = str(result)
            processed_results.append(error_result)
        else:
            processed_results.append(result)

    return processed_results
