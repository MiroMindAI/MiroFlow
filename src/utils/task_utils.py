# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Task execution utilities for benchmark evaluation."""

import asyncio
from pathlib import Path
from typing import List, Optional

from omegaconf import DictConfig

from src.agents.base_module import BaseAgentModule
from src.logging.task_tracer import (
    TaskContextVar,
    get_tracer,
    reset_current_task_context_var,
    set_current_task_context_var,
)
from src.utils.eval_utils import (
    AttemptResult,
    Evaluator,
    TaskResult,
    Task,
    STATUS_PENDING,
    STATUS_FAILED,
    STATUS_COMPLETED
)
tracer = get_tracer()

async def run_single_attempt(
    cfg: DictConfig,
    agent: BaseAgentModule,
    task: Task,
    attempt_id: int,
    evaluator: Optional[Evaluator] = None,
) -> AttemptResult:
    """Execute a single task attempt with optional evaluation."""
    
    attempt_result = AttemptResult(task=task, attempt_id=attempt_id)
    
    # Setup tracer and context
    log_path = Path(cfg.output_dir) / f"task_{task.task_id}_attempt_{attempt_id}.json"
    task_context_var = TaskContextVar(task_id=task.task_id, run_id=str(attempt_id))
    token = set_current_task_context_var(task_context_var)
    tracer = get_tracer()
    tracer.update_task_meta(
        patch={
            "task_id": task.task_id,
            "run_id": str(attempt_id),
            "task_description": task.task_question,
            "task_file_name": task.file_path or "",
        }
    )
    
    tracer.start()
    try:
        response = await agent.run({
            "task_description": task.task_question,
            "task_file_name": task.file_path or "",
        })
        
        attempt_result.update_from_response(response, log_path)
        tracer.update_task_meta(patch={"final_boxed_answer": attempt_result.model_boxed_answer})
        # Finish with completed status if no exception
        tracer.finish(status="completed")
    except Exception as e:
        attempt_result.status = STATUS_FAILED
        attempt_result.error_message = str(e)
        print(f"    Error in attempt {attempt_id}: {e}")
        tracer.finish(status="failed", error=str(e))    
    finally:
        # Reset context after all tracer operations are done
        reset_current_task_context_var(token)
    
    # Perform verification if evaluator is provided
    if evaluator is not None:
        attempt_result = await evaluator.verify_attempt_result(
            task, attempt_id, attempt_result
        )
    
    return attempt_result


async def run_single_task(
    cfg: DictConfig,
    agent: BaseAgentModule,
    task: Task,
    attempt_num: int = 1,
    evaluator: Optional[Evaluator] = None,
) -> TaskResult:
    """Run a single task with optional pass@k evaluation."""
    
    pass_at_k = evaluator.pass_at_k if evaluator else attempt_num
    print(f"Processing task {task.task_id} with pass@{pass_at_k}")
    
    result = TaskResult(task=task)
    found_correct = False
    
    try:
        for attempt_id in range(1, pass_at_k + 1):
            print(f"  Attempt {attempt_id}/{pass_at_k} for task {task.task_id}")
            
            attempt_result = await run_single_attempt(
                cfg=cfg,
                agent=agent,
                task=task,
                attempt_id=attempt_id,
                evaluator=evaluator,
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
            
            # Early stopping when correct answer is found
            if evaluator and attempt_result.is_correct:
                found_correct = True
                print(f"    🎯 Found correct answer! Stopping early after {attempt_id} attempts.")
                break
    except Exception as e:
        result.status = STATUS_FAILED
        result.error_message = str(e)
        print(f"Error processing task {task.task_id}: {e}")
        
    finally:
        result.pass_at_k_success = found_correct
        
        # Set judge result based on evaluation outcome
        if evaluator:
            result.judge_result = "PASS_AT_K_SUCCESS" if found_correct else "PASS_AT_K_FAILED"
            status_icon = "✅ SUCCESS" if found_correct else "❌ FAILED"
            print(f"    Pass@{pass_at_k} result: {status_icon}")
        
        print(f"Task {task.task_id} completed with {len(result.attempts)} attempts")
    
    return result

async def run_tasks(
    cfg: DictConfig,
    agent: BaseAgentModule,
    tasks: List[Task],
    evaluator: Optional[Evaluator] = None,
    max_concurrent: int = 3,
) -> List[TaskResult]:
    """Run multiple tasks in parallel with concurrency control."""
    
    print(f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent}")
    
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def run_with_semaphore(task: Task) -> TaskResult:
        async with semaphore:
            return await run_single_task(cfg=cfg, agent=agent, task=task, evaluator=evaluator)
    
    # Run tasks in parallel with semaphore control
    results = await asyncio.gather(
        *[run_with_semaphore(task) for task in tasks],
        return_exceptions=True,
    )
    
    return results
