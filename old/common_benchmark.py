# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import json
from pathlib import Path

import dotenv
from omegaconf import DictConfig, OmegaConf

from config import load_config

from src.utils.eval_utils import (
    Task,
    Evaluator,
)
from src.utils.task_utils import run_tasks
from src.agents.registry import build_agent_from_config
from src.logging.task_tracer import get_tracer


async def run_benchmark(cfg: DictConfig) -> float:
    """
    Main entry point for running benchmarks with Hydra.
    """
    print("Benchmark configuration:\n", OmegaConf.to_yaml(cfg, resolve=True))

    tracer = get_tracer()
    tracer.set_log_path(cfg.output_dir)

    # 读 benchmark 的 task
    def parse_func(x: str) -> Task:
        data = json.loads(x)

        return Task(
            task_id=data["task_id"],
            task_question=data["task_question"],
            ground_truth=data["ground_truth"],
            file_path=data.get("file_path"),
            metadata=data.get("metadata", {}),
        )

    evaluator = Evaluator(
        cfg=cfg.benchmark,
        parse_func=parse_func,
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

    results = await run_tasks(
        cfg=cfg,
        evaluator=evaluator,
        tasks=tasks,
        agent=agent,
        max_concurrent=cfg.benchmark.execution.max_concurrent,
    )

    # 计算测试结果正确性
    print("Evaluating accuracy...")
    accuracy = await evaluator.evaluate_accuracy(results)
    print(f"\nOverall pass@{evaluator.pass_at_k} accuracy: {accuracy:.2%}")

    # 输出测试精度
    output_filename = "benchmark_results.jsonl"
    log_dir = Path(cfg.output_dir)
    results_path = log_dir / output_filename
    evaluator.save_results(results, results_path)
    print(f"\nEvaluation completed! Results saved to {results_path}")

    # save accuracy to a file
    accuracy_file = (
        results_path.parent
        / f"{results_path.stem}_pass_at_{evaluator.pass_at_k}_accuracy.txt"
    )
    with open(accuracy_file, "w") as f:
        f.write(f"{accuracy:.2%}")

    return accuracy


def main(*args, config_file_name: str = ""):
    # Load environment variables
    dotenv.load_dotenv()

    # Load configuration
    cfg = load_config(config_file_name, *args)

    # Run benchmark
    asyncio.run(run_benchmark(cfg))
