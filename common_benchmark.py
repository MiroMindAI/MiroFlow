# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
import os
import random
import signal
from pathlib import Path
from typing import List

import dotenv
import hydra
from omegaconf import DictConfig, OmegaConf

from src.utils.eval_utils import (
    BenchmarkTask,
    BenchmarkResult,
    BenchmarkEvaluator,
)
from src.utils.task_utils import (
    run_single_task_attempt,
    scan_latest_attempt,
    verify_attempt_result,
    update_result_with_attempt,
    TaskStatus,
)
from src.logging.logger import (
    bootstrap_logger,
    init_logging_for_benchmark_evaluation,
    task_logging_context,
)
from src.agents.registry import build_agent_from_config
from src.agents.base_module import BaseAgentModule
from config import config_name, config_path

init_logging_for_benchmark_evaluation(print_task_logs=False)


async def run_single_task(
    cfg: DictConfig, 
    evaluator: BenchmarkEvaluator, 
    task: BenchmarkTask, 
    agent: BaseAgentModule
) -> BenchmarkResult:
    """
    Run inference for a single benchmark task with pass@k support

    Args:
        evaluator: BenchmarkEvaluator instance
        task: BenchmarkTask object
        agent: Agent instance for running tasks

    Returns:
        BenchmarkResult object
    """
    print(f"Processing task {task.task_id} with pass@{evaluator.pass_at_k}")

    result = BenchmarkResult(cfg=cfg, task=task)

    found_correct_answer = False

    try:
        # Prepare task
        task_description, task_file_path = evaluator.prepare_task_description(task)

        # Run up to k attempts (with early stopping when correct answer found)
        for attempt in range(1, evaluator.pass_at_k + 1):
            print(f"  Attempt {attempt}/{evaluator.pass_at_k} for task {task.task_id}")

            attempt_result = scan_latest_attempt(evaluator, task, attempt)
            # Run inference if no existing result
            if attempt_result["status"] in (TaskStatus.PENDING, TaskStatus.RUN_FAILED):
                attempt_result = await run_single_task_attempt(
                    attempt_result=attempt_result,
                    evaluator_output_dir=evaluator.output_dir,
                    task_id=task.task_id,
                    attempt=attempt,
                    task_description=task_description,
                    task_file_path=task_file_path,
                    agent=agent,
                )

            # Perform LLM verification if we have an answer and haven't verified yet
            if attempt_result["status"] == TaskStatus.RUN_COMPLETED:
                attempt_result = await verify_attempt_result(
                    evaluator, task, attempt, attempt_result
                )
            else:
                print(f"    ⚠️  Attempt {attempt}: No valid answer to verify")
            
            # Check if this attempt is correct
            if attempt_result.get("is_correct", False):
                found_correct_answer = True

            # Update result with this attempt
            update_result_with_attempt(result, attempt_result, attempt)

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
            f"    Pass@{evaluator.pass_at_k} result: {'✅ SUCCESS' if found_correct_answer else '❌ FAILED'}"
        )

    return result


async def run_parallel_inference(
    evaluator: BenchmarkEvaluator,
    tasks: List[BenchmarkTask],
    agent: BaseAgentModule,
    max_concurrent: int = 3,
) -> List[BenchmarkResult]:
    """Run inference on multiple tasks in parallel"""
    print(
        f"Running inference on {len(tasks)} tasks with max_concurrent={max_concurrent}"
    )

    semaphore = asyncio.Semaphore(max_concurrent)

    async def run_with_semaphore(task):
        async with semaphore:
            with task_logging_context(task.task_id, evaluator.output_dir):
                result = await run_single_task(
                    cfg=evaluator.cfg, 
                    evaluator=evaluator, 
                    task=task, 
                    agent=agent)
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
            # Create a temporary task object for error result
            error_task = BenchmarkTask(
                task_id=shuffled_tasks[i].task_id,
                task_question=shuffled_tasks[i].task_question,
                ground_truth=shuffled_tasks[i].ground_truth,
                file_path=shuffled_tasks[i].file_path,
                metadata=shuffled_tasks[i].metadata.copy(),
            )
            error_result = BenchmarkResult(cfg=evaluator.cfg, task=error_task)
            error_result.status = "failed"
            error_result.error_message = str(result)
            processed_results.append(error_result)
        else:
            processed_results.append(result)

    return processed_results


async def entrypoint(cfg: DictConfig) -> float:
    """
    Main entry point for running benchmarks with Hydra.
    """
    print("Benchmark configuration:\n", OmegaConf.to_yaml(cfg, resolve=True))

    # 读 benchmark 的 task
    def parse_func(x: str) -> BenchmarkTask:
        data = json.loads(x)
        file_path = data.get("file_path")
        if file_path is not None:
            path = Path(file_path)
            if path.is_absolute():
                file_path = str(path)
            else:
                file_path = str(Path(cfg.benchmark.data.data_dir) / path)
        
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

    evaluator = BenchmarkEvaluator(
        data_dir=cfg.benchmark.data.data_dir,
        benchmark_name=cfg.benchmark.name,
        cfg=cfg,
        metadata_file=cfg.benchmark.data.metadata_file,
        parse_func=parse_func,
        filter_func=filter_func,
    )

    # 读 benchmark 的 task
    print(f"Starting evaluation for benchmark: {cfg.benchmark.name}")
    tasks = evaluator.load_tasks()
    if len(tasks) == 0:
        print("No tasks loaded. Exiting.")
        return 0.0

    # 实例化 agent
    agent = build_agent_from_config(cfg=cfg)

    # 测试 benchmark 里的 task
    print(
        f"\nStarting parallel inference with {cfg.benchmark.execution.max_concurrent} concurrent tasks..."
    )
    print(f"Using pass@{evaluator.pass_at_k} evaluation...")
    results = await run_parallel_inference(
        evaluator,
        tasks,
        agent,
        max_concurrent=cfg.benchmark.execution.max_concurrent,
    )
    evaluator.results = results

    # 计算测试结果正确性
    print("Evaluating accuracy...")
    accuracy = await evaluator.evaluate_accuracy()
    print(f"\nOverall pass@{evaluator.pass_at_k} accuracy: {accuracy:.2%}")

    # 输出测试精度
    output_filename = "benchmark_results.jsonl"
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
        #exit()
        #cfg = OmegaConf.load(f"config/{chosen_config_name}.yaml")
        #exit()
        cfg = setup_hydra_output_dir(cfg, list(args))
        cfg = OmegaConf.create(OmegaConf.to_container(cfg, resolve=True))

        _ = bootstrap_logger(level=LOGGER_LEVEL)
        # Tracing functionality removed - miroflow-contrib deleted
        
        asyncio.run(entrypoint(cfg))
