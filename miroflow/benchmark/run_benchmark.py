# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import argparse
import asyncio
import json
import os
import signal
from pathlib import Path

import dotenv
from omegaconf import DictConfig, OmegaConf

# from config import load_config, config_name, config_path
from config import load_config
from miroflow.benchmark.eval_utils import (
    Task,
    Evaluator,
)
from miroflow.benchmark.task_runner import run_tasks, _cleanup_executor
from miroflow.agents import build_agent_from_config
from miroflow.logging.task_tracer import get_tracer, set_tracer


_main_signal_received = False


def _main_signal_handler(signum, frame):
    """Handle termination signals in main process (non-reentrant)."""
    global _main_signal_received
    if _main_signal_received:
        # Already handling a signal, force exit to avoid nested sys.exit()
        os._exit(128 + signum)
    _main_signal_received = True
    signal_name = signal.Signals(signum).name
    print(f"\n⚠️ Main process received {signal_name}, cleaning up...")
    _cleanup_executor()
    os._exit(128 + signum)


async def test_benchmark(cfg: DictConfig) -> float:
    """
    Main entry point for running benchmarks with Hydra.
    """
    print("Benchmark configuration:\n", OmegaConf.to_yaml(cfg, resolve=True))

    tracer = get_tracer()
    tracer.set_log_path(cfg.output_dir)

    # Load benchmark tasks
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

    # Load benchmark tasks
    print(f"Starting evaluation for benchmark: {cfg.benchmark.name}")
    tasks = evaluator.load_tasks()
    if len(tasks) == 0:
        print("No tasks loaded. Exiting.")
        return 0.0

    # Instantiate agent
    agent = build_agent_from_config(cfg=cfg)
    # Test benchmark tasks
    print(
        f"\nStarting parallel inference with {cfg.benchmark.execution.max_concurrent} concurrent tasks..."
    )
    print(f"Using pass@{evaluator.pass_at_k} evaluation...")

    execution_cfg = cfg.benchmark.execution
    results = run_tasks(
        cfg=cfg,
        agent=agent,
        tasks=tasks,
        evaluator=evaluator,
        max_concurrent=execution_cfg.max_concurrent,
        pass_at_k=execution_cfg.get("pass_at_k", 1),
        max_retry=execution_cfg.get("max_retry", 1),
        exceed_max_turn_summary=execution_cfg.get("exceed_max_turn_summary", False),
        prompt_manager=agent.prompt_manager
        if hasattr(agent, "prompt_manager")
        else None,
    )

    # Calculate test result accuracy
    print("Evaluating accuracy...")
    accuracy = await evaluator.evaluate_accuracy(results)
    print(f"\nOverall pass@{evaluator.pass_at_k} accuracy: {accuracy:.2%}")

    # Output test accuracy
    log_dir = Path(cfg.output_dir)
    results_path = log_dir / "benchmark_results.jsonl"
    evaluator.save_results(results, results_path)
    print(f"\nEvaluation completed! Results saved to {results_path}")

    # save accuracy to a file
    accuracy_file = (
        log_dir / f"{results_path.stem}_pass_at_{evaluator.pass_at_k}_accuracy.txt"
    )
    with open(accuracy_file, "w") as f:
        f.write(f"{accuracy:.2%}")

    return accuracy


if __name__ == "__main__":
    # Register signal handlers for main process (only when run as main script)
    signal.signal(signal.SIGTERM, _main_signal_handler)
    signal.signal(signal.SIGINT, _main_signal_handler)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Run benchmark evaluation")
    parser.add_argument(
        "--config-path", type=str, default="", help="Configuration file path or name"
    )
    parser.add_argument(
        "overrides", nargs="*", help="Additional configuration overrides"
    )
    args = parser.parse_args()

    # Load environment variables
    dotenv.load_dotenv()

    # Load configuration
    cfg = load_config(args.config_path, *args.overrides)

    # Set tracer for logging
    set_tracer(cfg.output_dir)

    # Run benchmark
    asyncio.run(test_benchmark(cfg))

# example:
# uv test_benchmark.py --config-path config/agent-gaia-validation-gpt5-single-agent.yaml
