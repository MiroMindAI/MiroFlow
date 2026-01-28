# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Task execution utilities for benchmark evaluation."""

import asyncio
from pathlib import Path
from typing import List, Optional

from omegaconf import DictConfig

from src.agents import BaseAgent
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
    STATUS_FAILED,
    STOP_CONDITION_CORRECT,
    STOP_CONDITION_VALID_BOX,
    STOP_CONDITION_MAX_TURN,
)

tracer = get_tracer()


def _build_failure_experience_text(
    failure_experiences: List[str],
    prompt_manager=None,
) -> str:
    """Build failure experience text from list of summaries."""
    if not failure_experiences:
        return ""

    if prompt_manager:
        header = prompt_manager.render_prompt("failure_experience_header", context={})
        footer = prompt_manager.render_prompt("failure_experience_footer", context={})
        items = []
        for i, summary in enumerate(failure_experiences, 1):
            item = prompt_manager.render_prompt(
                "failure_experience_item",
                context={"attempt_number": i, "failure_summary": summary},
            )
            items.append(item)
        return f"{header}\n{''.join(items)}\n{footer}"
    else:
        header = "=== Previous Attempts Analysis ===\n"
        header += (
            "The following summarizes what was tried before and why it did not work.\n"
        )
        header += (
            "Use this to guide a NEW approach. Avoid repeating the same mistakes.\n"
        )
        items = []
        for i, summary in enumerate(failure_experiences, 1):
            items.append(f"[Attempt {i}]\n{summary}\n")
        footer = "=== End of Previous Attempts ===\n"
        footer += "Based on the above analysis, try a different approach.\n"
        return f"{header}\n{''.join(items)}\n{footer}"


def _check_stop_condition(
    stop_condition: str,
    attempt_result: AttemptResult,
) -> bool:
    """Check if the stop condition is met based on the attempt result."""
    if stop_condition == STOP_CONDITION_CORRECT:
        return attempt_result.is_correct
    elif stop_condition == STOP_CONDITION_VALID_BOX:
        return attempt_result.is_valid_box
    elif stop_condition == STOP_CONDITION_MAX_TURN:
        return False
    return False


async def run_single_attempt(
    cfg: DictConfig,
    agent: BaseAgent,
    task: Task,
    attempt_id: int,
    evaluator: Optional[Evaluator] = None,
    failure_experiences: Optional[List[str]] = None,
    prompt_manager=None,
) -> AttemptResult:
    """Execute a single task attempt with optional evaluation."""

    attempt_result = AttemptResult(task=task, attempt_id=attempt_id)

    log_path = Path(cfg.output_dir) / f"task_{task.task_id}_attempt_{attempt_id}.json"
    task_context_var = TaskContextVar(task_id=task.task_id, run_id=str(attempt_id))
    token = set_current_task_context_var(task_context_var)
    tracer = get_tracer()

    retry_with_experience = bool(failure_experiences)
    previous_attempt_ids = list(range(1, attempt_id)) if failure_experiences else []

    tracer.update_task_meta(
        patch={
            "task_id": task.task_id,
            "run_id": str(attempt_id),
            "task_description": task.task_question,
            "task_file_name": task.file_path or "",
            "ground_truth": task.ground_truth,
            "retry_with_experience": retry_with_experience,
            "previous_attempt_ids": previous_attempt_ids,
        }
    )

    task_description = task.task_question
    if failure_experiences:
        experience_text = _build_failure_experience_text(
            failure_experiences, prompt_manager
        )
        task_description = f"{experience_text}\n\n{task.task_question}"
        attempt_result.used_failure_experiences = failure_experiences

    tracer.start()
    try:
        response = await agent.run(
            {
                "task_description": task_description,
                "task_file_name": task.file_path or "",
            }
        )

        attempt_result.update_from_response(response, log_path)
        tracer.update_task_meta(
            patch={
                "final_boxed_answer": attempt_result.model_boxed_answer,
                "is_valid_box": attempt_result.is_valid_box,
                "failure_experience_summary": attempt_result.failure_experience_summary,
            }
        )

        if evaluator is not None:
            attempt_result = await evaluator.verify_attempt_result(
                task, attempt_id, attempt_result
            )
            tracer.update_task_meta(
                patch={
                    "judge_result": attempt_result.judge_result,
                }
            )

        tracer.finish(status="completed")
    except Exception as e:
        attempt_result.status = STATUS_FAILED
        attempt_result.error_message = str(e)
        print(f"    Error in attempt {attempt_id}: {e}")
        tracer.finish(status="failed", error=str(e))
    finally:
        reset_current_task_context_var(token)

    return attempt_result


async def run_single_task(
    cfg: DictConfig,
    agent: BaseAgent,
    task: Task,
    attempt_num: int = 1,
    evaluator: Optional[Evaluator] = None,
    stop_condition: str = STOP_CONDITION_CORRECT,
    enable_failure_experience: bool = False,
    prompt_manager=None,
) -> TaskResult:
    """Run a single task with optional pass@k evaluation and failure experience."""

    pass_at_k = evaluator.pass_at_k if evaluator else attempt_num
    print(f"Processing task {task.task_id} with pass@{pass_at_k}")

    result = TaskResult(task=task)
    result.stop_condition = stop_condition
    found_correct = False
    should_stop = False
    failure_experiences: List[str] = []

    try:
        for attempt_id in range(1, pass_at_k + 1):
            print(f"  Attempt {attempt_id}/{pass_at_k} for task {task.task_id}")

            current_experiences = (
                failure_experiences if enable_failure_experience else None
            )

            attempt_result = await run_single_attempt(
                cfg=cfg,
                agent=agent,
                task=task,
                attempt_id=attempt_id,
                evaluator=evaluator,
                failure_experiences=current_experiences,
                prompt_manager=prompt_manager,
            )

            result.update_with_attempt(attempt_result)

            should_stop = _check_stop_condition(stop_condition, attempt_result)

            if should_stop:
                attempt_result.stop_reason = stop_condition
                if attempt_result.is_correct:
                    found_correct = True
                print(
                    f"    Stop condition '{stop_condition}' met after {attempt_id} attempts."
                )
                break

            if (
                enable_failure_experience
                and attempt_id < pass_at_k
                and attempt_result.failure_experience_summary
            ):
                failure_experiences.append(attempt_result.failure_experience_summary)
                result.total_failure_experiences = len(failure_experiences)
                print(f"    Collected failure experience #{len(failure_experiences)}")

    except Exception as e:
        result.status = STATUS_FAILED
        result.error_message = str(e)
        print(f"Error processing task {task.task_id}: {e}")

    finally:
        result.pass_at_k_success = found_correct

        if evaluator:
            result.judge_result = (
                "PASS_AT_K_SUCCESS" if found_correct else "PASS_AT_K_FAILED"
            )
            status_icon = "✅ SUCCESS" if found_correct else "❌ FAILED"
            print(f"    Pass@{pass_at_k} result: {status_icon}")

        print(f"Task {task.task_id} completed with {len(result.attempts)} attempts")

    return result


async def run_tasks(
    cfg: DictConfig,
    agent: BaseAgent,
    tasks: List[Task],
    evaluator: Optional[Evaluator] = None,
    max_concurrent: int = 3,
    stop_condition: str = STOP_CONDITION_CORRECT,
    enable_failure_experience: bool = False,
    prompt_manager=None,
) -> List[TaskResult]:
    """Run multiple tasks in parallel with concurrency control."""

    print(
        f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent}"
    )

    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(task: Task) -> TaskResult:
        async with semaphore:
            return await run_single_task(
                cfg=cfg,
                agent=agent,
                task=task,
                evaluator=evaluator,
                stop_condition=stop_condition,
                enable_failure_experience=enable_failure_experience,
                prompt_manager=prompt_manager,
            )

    results = await asyncio.gather(
        *[run_with_semaphore(task) for task in tasks],
        return_exceptions=True,
    )

    return results
