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

from config import load_config

from src.utils.eval_utils import (
    BenchmarkTask,
    BenchmarkResult,
    BenchmarkEvaluator,
    TaskStatus,
)
from src.utils.task_utils import run_tasks
from src.agents.registry import build_agent_from_config
from src.agents.base_module import BaseAgentModule
from config import config_name, config_path
from src.logging.task_tracer import get_tracer


async def run_benchmark(cfg: DictConfig) -> float:
    """
    Main entry point for running benchmarks with Hydra.
    """
    print("Benchmark configuration:\n", OmegaConf.to_yaml(cfg, resolve=True))

    tracer = get_tracer()
    tracer.set_log_path(cfg.output_dir)

    # 读 benchmark 的 task
    def parse_func(x: str) -> BenchmarkTask:
        data = json.loads(x)
        
        return BenchmarkTask(
            task_id=data["task_id"],
            task_question=data["task_question"],
            ground_truth=data["ground_truth"],
            file_path=data.get("file_path"),
            metadata=data.get("metadata", {}),
        )

    evaluator = BenchmarkEvaluator(
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
    print(f"\nStarting parallel inference with {cfg.benchmark.execution.max_concurrent} concurrent tasks...")
    print(f"Using pass@{evaluator.pass_at_k} evaluation...")
    
    results = await run_tasks(
        cfg=cfg,
        evaluator=evaluator,
        tasks=tasks,
        agent=agent,
        max_concurrent=cfg.benchmark.execution.max_concurrent,
    )
    evaluator.results = results

    # 计算测试结果正确性
    print("Evaluating accuracy...")
    accuracy = await evaluator.evaluate_accuracy()
    print(f"\nOverall pass@{evaluator.pass_at_k} accuracy: {accuracy:.2%}")

    # 输出测试精度
    output_filename = "benchmark_results.jsonl"
    log_dir = Path(cfg.output_dir)
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



def main(*args, config_file_name: str = ""):
    # Load environment variables
    dotenv.load_dotenv()

    # Load configuration
    cfg = load_config(config_file_name, *args)

    # Run benchmark 
    asyncio.run(run_benchmark(cfg))
