#!/usr/bin/env python3
"""
Run a single task with the configured agent.

Usage:
    python run_single_task.py --config config/standard_gaia-validation-text-103_kimi_k25.yaml --task-id <task_id>
    python run_single_task.py --config config/standard_gaia-validation-text-103_kimi_k25.yaml --task-question "What is 2+2?"
    python run_single_task.py --config config/standard_gaia-validation-text-103_kimi_k25.yaml --task-index 0
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

import dotenv
from omegaconf import DictConfig

from config import load_config
from src.benchmark.eval_utils import Task, Evaluator
from src.benchmark.task_runner import run_single_task as _run_single_task
from src.agents import build_agent_from_config
from src.logging.task_tracer import get_tracer


def parse_task_from_json(x: str) -> Task:
    """Parse a task from a JSON string."""
    data = json.loads(x)
    return Task(
        task_id=data["task_id"],
        task_question=data["task_question"],
        ground_truth=data["ground_truth"],
        file_path=data.get("file_path"),
        metadata=data.get("metadata", {}),
    )


def test_single_task(cfg: DictConfig, task: Task):
    """Test a single task with the configured agent."""

    print("=" * 80)
    print("Testing Single Task")
    print("=" * 80)
    print(f"Task ID: {task.task_id}")
    print(f"Question: {task.task_question}")
    if task.file_path:
        print(f"File Path: {task.file_path}")
    if task.ground_truth:
        print(f"Ground Truth: {task.ground_truth}")
    print("=" * 80)

    # Set up output directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(cfg.output_dir) / f"single_task_{task.task_id}_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    tracer = get_tracer()
    tracer.set_log_path(str(output_dir))

    # Only create evaluator when ground truth is provided
    evaluator = None
    if task.ground_truth:
        evaluator = Evaluator(
            cfg=cfg.benchmark,
            parse_func=parse_task_from_json,
        )

    # Instantiate agent
    print("\nInitializing agent...")
    agent = build_agent_from_config(cfg=cfg)
    print(f"Agent initialized: {agent.__class__.__name__}")

    # Run the single task
    print("\nRunning task...")
    execution_cfg = cfg.benchmark.execution

    result = asyncio.run(
        _run_single_task(
            cfg=cfg,
            agent=agent,
            task=task,
            pass_at_k=1,
            max_retry=execution_cfg.get("max_retry", 1),
            evaluator=evaluator,
            exceed_max_turn_summary=execution_cfg.get(
                "exceed_max_turn_summary", False
            ),
            prompt_manager=agent.prompt_manager
            if hasattr(agent, "prompt_manager")
            else None,
        )
    )

    # Display results
    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)

    print(f"Status: {result.status}")
    print(f"Final Answer: {result.model_boxed_answer or 'N/A'}")
    if task.ground_truth:
        print(f"Ground Truth: {task.ground_truth}")
        print(f"Correct: {result.judge_result or 'N/A'}")

    if result.error_message:
        print(f"Error: {result.error_message}")

    print(f"\nOutput directory: {output_dir}")

    # Find and display the log file
    log_files = list(output_dir.glob("task_*.json"))
    if log_files:
        print(f"Task log: {log_files[0]}")

    print("=" * 80)

    return result


def main():
    parser = argparse.ArgumentParser(description="Test a single task")
    parser.add_argument(
        "--config-path",
        "--config",
        type=str,
        required=True,
        help="Path to configuration file (e.g., config/standard_gaia-validation-text-103_kimi_k25.yaml)",
    )
    parser.add_argument(
        "--task-id",
        type=str,
        help="Specific task ID to run",
    )
    parser.add_argument(
        "--task-question",
        type=str,
        help="Task question to run (if task-id not provided)",
    )
    parser.add_argument(
        "--task-index",
        type=int,
        help="Index of task in benchmark file (0-based)",
    )
    parser.add_argument(
        "--ground-truth",
        type=str,
        help="Ground truth answer (optional, for custom questions)",
    )
    parser.add_argument(
        "--file-path",
        type=str,
        nargs="+",
        help="Path(s) to attached file(s) for the task",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="logs/single_task_tests",
        help="Output directory for logs",
    )

    args = parser.parse_args()

    # Load environment variables
    dotenv.load_dotenv()

    # Load configuration
    print(f"Loading configuration from: {args.config_path}")
    cfg = load_config(args.config_path, f"output_dir={args.output_dir}")

    # Determine which task to run
    task = None

    if args.task_id or args.task_index is not None:
        # Load task from benchmark file
        evaluator = Evaluator(cfg=cfg.benchmark, parse_func=parse_task_from_json)
        all_tasks = evaluator.load_tasks()

        if args.task_index is not None:
            if 0 <= args.task_index < len(all_tasks):
                task = all_tasks[args.task_index]
                print(f"Selected task at index {args.task_index}")
            else:
                print(
                    f"Error: Task index {args.task_index} out of range (0-{len(all_tasks)-1})"
                )
                sys.exit(1)
        elif args.task_id:
            matching_tasks = [t for t in all_tasks if t.task_id == args.task_id]
            if matching_tasks:
                task = matching_tasks[0]
                print(f"Found task with ID: {args.task_id}")
            else:
                print(f"Error: Task with ID '{args.task_id}' not found")
                print(f"Available task IDs: {[t.task_id for t in all_tasks[:5]]}...")
                sys.exit(1)

    elif args.task_question:
        # Create a custom task
        import uuid

        file_path = args.file_path
        if file_path and len(file_path) == 1:
            file_path = file_path[0]
        task = Task(
            task_id=str(uuid.uuid4()),
            task_question=args.task_question,
            ground_truth=args.ground_truth or "",
            file_path=file_path,
            metadata={},
        )
        print("Created custom task")

    else:
        print("Error: Must provide --task-id, --task-index, or --task-question")
        parser.print_help()
        sys.exit(1)

    # Run the task
    result = test_single_task(cfg, task)

    # Exit with appropriate code
    if result.status == "completed":
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
