# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

"""Task execution utilities for benchmark evaluation."""

import asyncio
import gc
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Optional

from omegaconf import DictConfig, OmegaConf

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
)

tracer = get_tracer()


def _task_worker(task_dict, cfg_dict, pass_at_k, max_retry, exceed_max_turn_summary):
    """
    Worker function for ProcessPoolExecutor.
    Must be at module level for pickling.
    Runs a single task in a separate process.
    """
    import json

    from omegaconf import OmegaConf

    from src.agents import build_agent_from_config
    from src.logging.task_tracer import set_tracer
    from src.utils.eval_utils import Evaluator, Task

    # Reconstruct config and task
    cfg = OmegaConf.create(cfg_dict)
    task = Task.from_dict(task_dict)

    # Set up tracer for this process
    set_tracer(cfg.output_dir)

    # Create agent in this process
    agent = build_agent_from_config(cfg)

    # Create evaluator with parse_func defined inline
    def parse_func(x: str) -> Task:
        data = json.loads(x)
        return Task(
            task_id=data["task_id"],
            task_question=data["task_question"],
            ground_truth=data["ground_truth"],
            file_path=data.get("file_path"),
            metadata=data.get("metadata", {}),
        )

    evaluator = Evaluator(cfg=cfg.benchmark, parse_func=parse_func)

    # Run in new event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.set_exception_handler(lambda _loop, _context: None)  # Suppress warnings

    try:
        result = loop.run_until_complete(
            run_single_task(
                cfg=cfg,
                agent=agent,
                task=task,
                pass_at_k=pass_at_k,
                max_retry=max_retry,
                evaluator=evaluator,
                exceed_max_turn_summary=exceed_max_turn_summary,
                prompt_manager=agent.prompt_manager
                if hasattr(agent, "prompt_manager")
                else None,
            )
        )
        return result.to_dict()
    finally:
        loop.close()
        gc.collect()


def _build_exceed_max_turn_summary_text(
    summaries: List[str],
    prompt_manager=None,
) -> str:
    """Build summary text from list of exceed max turn summaries."""
    if not summaries:
        return ""

    if prompt_manager:
        header = prompt_manager.render_prompt(
            "exceed_max_turn_summary_header", context={}
        )
        footer = prompt_manager.render_prompt(
            "exceed_max_turn_summary_footer", context={}
        )
        items = []
        for i, summary in enumerate(summaries, 1):
            item = prompt_manager.render_prompt(
                "exceed_max_turn_summary_item",
                context={"attempt_number": i, "summary": summary},
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
        for i, summary in enumerate(summaries, 1):
            items.append(f"[Attempt {i}]\n{summary}\n")
        footer = "=== End of Previous Attempts ===\n"
        footer += "Based on the above analysis, try a different approach.\n"
        return f"{header}\n{''.join(items)}\n{footer}"


async def run_single_retry(
    cfg: DictConfig,
    agent: BaseAgent,
    task: Task,
    attempt_id: int,
    retry_id: int,
    evaluator: Optional[Evaluator] = None,
    previous_summaries: Optional[List[str]] = None,
    prompt_manager=None,
) -> AttemptResult:
    """Execute a single retry within an attempt."""

    attempt_result = AttemptResult(task=task, attempt_id=attempt_id, retry_id=retry_id)

    log_path = (
        Path(cfg.output_dir)
        / f"task_{task.task_id}_attempt_{attempt_id}_retry_{retry_id}.json"
    )
    task_context_var = TaskContextVar(
        task_id=task.task_id,
        attempt_id=attempt_id,
        retry_id=retry_id,
    )
    token = set_current_task_context_var(task_context_var)
    tracer = get_tracer()

    used_exceed_max_turn_summaries = bool(previous_summaries)
    previous_retry_ids = list(range(retry_id)) if previous_summaries else []

    tracer.update_task_meta(
        patch={
            "task_id": task.task_id,
            "attempt_id": attempt_id,
            "retry_id": retry_id,
            "task_description": task.task_question,
            "task_file_name": task.file_path or "",
            "ground_truth": task.ground_truth,
            "used_exceed_max_turn_summaries": used_exceed_max_turn_summaries,
            "previous_retry_ids": previous_retry_ids,
        }
    )

    task_description = task.task_question
    if previous_summaries:
        summary_text = _build_exceed_max_turn_summary_text(
            previous_summaries, prompt_manager
        )
        task_description = f"{summary_text}\n\n{task.task_question}"
        attempt_result.used_exceed_max_turn_summaries = previous_summaries

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
                "exceed_max_turn_summary": attempt_result.exceed_max_turn_summary,
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
        print(f"    Error in attempt {attempt_id} retry {retry_id}: {e}")
        tracer.finish(status="failed", error=str(e))
    finally:
        reset_current_task_context_var(token)

    return attempt_result


async def run_single_task(
    cfg: DictConfig,
    agent: BaseAgent,
    task: Task,
    pass_at_k: int = 1,
    max_retry: int = 1,
    evaluator: Optional[Evaluator] = None,
    exceed_max_turn_summary: bool = False,
    prompt_manager=None,
) -> TaskResult:
    """Run a single task with pass@k attempts and retry logic.

    Args:
        cfg: Configuration object.
        agent: The agent to run.
        task: The task to execute.
        pass_at_k: Number of attempts (outer loop, stops on correct answer).
        max_retry: Number of retries per attempt (inner loop, stops on valid_box).
        evaluator: Optional evaluator for judging correctness.
        exceed_max_turn_summary: Whether to generate failure summaries for retries.
        prompt_manager: Optional prompt manager for rendering templates.

    Returns:
        TaskResult containing all attempts and final status.
    """

    print(
        f"Processing task {task.task_id} with pass@{pass_at_k}, max_retry={max_retry}"
    )

    result = TaskResult(task=task)
    found_correct = False

    try:
        for attempt_id in range(1, pass_at_k + 1):
            print(f"  Attempt {attempt_id}/{pass_at_k} for task {task.task_id}")
            result.total_attempts = attempt_id

            collected_summaries: List[str] = []

            for retry_id in range(max_retry):
                print(f"    Retry {retry_id}/{max_retry - 1}")
                result.total_retries += 1

                current_summaries = (
                    collected_summaries if exceed_max_turn_summary else None
                )

                retry_result = await run_single_retry(
                    cfg=cfg,
                    agent=agent,
                    task=task,
                    attempt_id=attempt_id,
                    retry_id=retry_id,
                    evaluator=evaluator,
                    previous_summaries=current_summaries,
                    prompt_manager=prompt_manager,
                )

                result.update_with_attempt(retry_result)

                if retry_result.is_valid_box:
                    print(f"    Got valid box at retry {retry_id}")

                    if retry_result.is_correct:
                        found_correct = True
                        print("    Answer is CORRECT!")
                    break

                if (
                    exceed_max_turn_summary
                    and retry_id < max_retry - 1
                    and retry_result.exceed_max_turn_summary
                ):
                    collected_summaries.append(retry_result.exceed_max_turn_summary)
                    print(f"    Collected summary #{len(collected_summaries)}")

            if found_correct:
                print(f"  Found correct answer at attempt {attempt_id}")
                break

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

        print(f"Task {task.task_id} completed with {len(result.attempts)} retries")

    return result


def run_tasks(
    cfg: DictConfig,
    agent: BaseAgent,
    tasks: List[Task],
    evaluator: Optional[Evaluator] = None,
    max_concurrent: int = 3,
    pass_at_k: int = 1,
    max_retry: int = 1,
    exceed_max_turn_summary: bool = False,
    prompt_manager=None,
) -> List[TaskResult]:
    """Run multiple tasks in parallel using ProcessPoolExecutor.

    Each task runs in a separate process with its own agent and evaluator,
    bypassing Python's GIL for true parallelism.
    """
    print(
        f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent} (multiprocessing)"
    )
    print(f"  pass@k={pass_at_k}, max_retry={max_retry}")

    # Serialize config for passing to worker processes
    cfg_dict = OmegaConf.to_container(cfg, resolve=True)

    # Shuffle tasks to avoid order bias and improve balancing
    shuffled_tasks = tasks.copy()
    random.shuffle(shuffled_tasks)

    # Prepare worker arguments
    worker_args = [
        (task.to_dict(), cfg_dict, pass_at_k, max_retry, exceed_max_turn_summary)
        for task in shuffled_tasks
    ]

    results_dict = {}
    executor = None

    try:
        executor = ProcessPoolExecutor(max_workers=max_concurrent)
        future_to_task_id = {
            executor.submit(_task_worker, *args): args[0]["task_id"]
            for args in worker_args
        }

        for future in as_completed(future_to_task_id):
            task_id = future_to_task_id[future]
            try:
                result_dict = future.result()
                result = TaskResult.from_dict(result_dict)
                results_dict[task_id] = result
                print(
                    f"Progress: {len(results_dict)}/{len(shuffled_tasks)} tasks completed"
                )
            except Exception as e:
                print(f"Exception in task {task_id}: {e}")
                # Create error result
                task_dict = next(
                    a[0] for a in worker_args if a[0]["task_id"] == task_id
                )
                error_result = TaskResult(task=Task.from_dict(task_dict))
                error_result.status = STATUS_FAILED
                error_result.error_message = str(e)
                results_dict[task_id] = error_result

    except KeyboardInterrupt:
        print("\n⚠️ Received interrupt, terminating workers...")
        if executor:
            for future in future_to_task_id:
                future.cancel()
            executor.shutdown(wait=False, cancel_futures=True)
        raise
    finally:
        if executor:
            try:
                executor.shutdown(wait=True)
            except Exception:
                pass

    # Sort results by original task order
    task_id_to_index = {task.task_id: i for i, task in enumerate(tasks)}
    results = [
        results_dict[task.task_id]
        for task in shuffled_tasks
        if task.task_id in results_dict
    ]
    results.sort(key=lambda r: task_id_to_index.get(r.task.task_id, len(tasks)))

    return results
