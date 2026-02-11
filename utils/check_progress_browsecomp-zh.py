#!/usr/bin/env python3
"""
BrowseComp-ZH Progress Checker (289 tasks version with time estimation)

This script analyzes BrowseComp-ZH results with:
- File format: task_{task_id}_attempt_{attempt_id}_retry_{retry_id}.json
- Time estimation based on completed tasks
- Shows pass@1, pass@2, pass@3 breakdown
- Shows retry statistics per attempt

Usage:
    python check_progress_browsecomp-zh.py [LOG_FOLDER_PATH]

Example:
    python check_progress_browsecomp-zh.py logs/browsecomp-zh/xxx
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Benchmark configuration
TASKS_PER_RUN = 289

# Precompile regex patterns for better performance
TASK_FILENAME_NEW_PATTERN = re.compile(r"task_(.+)_attempt_(\d+)_retry_(\d+)\.json$")
TASK_FILENAME_OLD_PATTERN = re.compile(r"task_(.+)_attempt_(\d+)\.json$")

PROGRESS_BAR_WIDTH = 20
GREEN_THRESHOLD = 80
YELLOW_THRESHOLD = 60
ORANGE_THRESHOLD = 40


def create_progress_bar(percentage: float, width: int = PROGRESS_BAR_WIDTH) -> str:
    """Create a visual progress bar for percentage display."""
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)

    if percentage >= GREEN_THRESHOLD:
        color = "\033[92m"
    elif percentage >= YELLOW_THRESHOLD:
        color = "\033[93m"
    elif percentage >= ORANGE_THRESHOLD:
        color = "\033[33m"
    else:
        color = "\033[91m"

    reset = "\033[0m"
    return f"{color}[{bar}] {percentage:.1f}%{reset}"


def parse_task_filename(filename: str) -> Optional[Tuple[str, int, int]]:
    """Parse task filename to extract task_id, attempt_id, and retry_id."""
    match = TASK_FILENAME_NEW_PATTERN.match(filename)
    if match:
        return match.group(1), int(match.group(2)), int(match.group(3))

    match = TASK_FILENAME_OLD_PATTERN.match(filename)
    if match:
        return match.group(1), int(match.group(2)), 0

    return None


def parse_timestamp(time_str: str) -> Optional[datetime]:
    """Parse ISO format timestamp string to datetime."""
    if not time_str:
        return None
    try:
        if time_str.endswith("Z"):
            time_str = time_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(time_str)
        return dt.replace(tzinfo=None)
    except (ValueError, TypeError):
        return None


def format_duration(minutes: float) -> str:
    """Format duration in minutes to human readable string."""
    if minutes < 60:
        return f"{int(minutes)} minutes"
    elif minutes < 1440:  # less than a day
        hours = minutes / 60
        return f"{hours:.1f} hours"
    else:
        days = minutes / 1440
        return f"{days:.1f} days"


@dataclass
class RetryResult:
    """Result for a single retry within an attempt."""

    retry_id: int
    status: str = ""
    judge_result: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    file_path: Optional[Path] = None


@dataclass
class AttemptResult:
    """Result for a single attempt (may contain multiple retries)."""

    attempt_id: int
    retries: List[RetryResult] = field(default_factory=list)
    passed: bool = False
    passed_at_retry: Optional[int] = None
    final_status: str = ""
    final_judge_result: str = ""


@dataclass
class TaskResult:
    """Result for a single task across all attempts and retries."""

    task_id: str
    attempts: Dict[int, AttemptResult] = field(default_factory=dict)
    passed_at_attempt: Optional[int] = None
    passed_at_retry: Optional[int] = None
    final_status: str = "unknown"
    final_judge_result: str = ""
    is_running: bool = False
    total_retries: int = 0
    earliest_start: Optional[datetime] = None
    latest_end: Optional[datetime] = None


@dataclass
class RunStats:
    """Statistics for a single run."""

    total_tasks: int = 0
    total_attempts: int = 0
    total_retries: int = 0

    running: int = 0
    completed: int = 0

    correct: int = 0
    incorrect: int = 0
    not_attempted: int = 0
    failed: int = 0
    other: int = 0

    pass_at_1: int = 0
    pass_at_2: int = 0
    pass_at_3: int = 0
    pass_at_higher: int = 0

    # Time tracking
    earliest_start: Optional[datetime] = None
    latest_end: Optional[datetime] = None
    completed_files: List[Path] = field(default_factory=list)

    correct_tasks: List[str] = field(default_factory=list)
    incorrect_tasks: List[str] = field(default_factory=list)
    not_attempted_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    other_tasks: List[str] = field(default_factory=list)
    running_tasks: List[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return (self.correct / self.completed * 100) if self.completed > 0 else 0.0


def find_task_files(log_folder: Path) -> Dict[str, Dict[str, List[Path]]]:
    """Find all task JSON files grouped by run and task_id."""
    runs: Dict[str, Dict[str, List[Path]]] = defaultdict(lambda: defaultdict(list))

    print("Scanning for task files...", end="", flush=True)
    file_count = 0

    for json_file in log_folder.rglob("task_*.json"):
        if "task_root" in json_file.name:
            continue

        parsed = parse_task_filename(json_file.name)
        if not parsed:
            continue

        file_count += 1
        task_id, _, _ = parsed

        for part in json_file.parts:
            if part.startswith("run_") and part[4:].isdigit():
                if json_file not in runs[part][task_id]:
                    runs[part][task_id].append(json_file)
                break

    task_count = sum(len(tasks) for tasks in runs.values())
    print(f" found {file_count} files, {task_count} unique tasks in {len(runs)} runs")
    return {run_id: dict(tasks) for run_id, tasks in runs.items()}


def load_attempt_data(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a single attempt JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None


def analyze_task_attempts(task_id: str, attempt_files: List[Path]) -> TaskResult:
    """Analyze all attempts and retries for a single task (checks latest retry only)."""
    result = TaskResult(task_id=task_id)

    for file_path in attempt_files:
        parsed = parse_task_filename(file_path.name)
        if not parsed:
            continue

        _, attempt_id, retry_id = parsed
        data = load_attempt_data(file_path)
        if not data:
            continue

        task_meta = data.get("task_meta", {})

        # Parse timestamps
        start_time = parse_timestamp(task_meta.get("start_time", ""))
        end_time = parse_timestamp(task_meta.get("end_time", ""))

        # Track earliest start and latest end
        if start_time:
            if result.earliest_start is None or start_time < result.earliest_start:
                result.earliest_start = start_time
        if end_time:
            if result.latest_end is None or end_time > result.latest_end:
                result.latest_end = end_time

        retry = RetryResult(
            retry_id=retry_id,
            status=task_meta.get("status", "").lower(),
            judge_result=task_meta.get("judge_result", "").upper(),
            start_time=start_time,
            end_time=end_time,
            file_path=file_path,
        )

        if attempt_id not in result.attempts:
            result.attempts[attempt_id] = AttemptResult(attempt_id=attempt_id)

        result.attempts[attempt_id].retries.append(retry)
        result.total_retries += 1

    for attempt in result.attempts.values():
        attempt.retries.sort(key=lambda x: x.retry_id)

    for attempt_id in sorted(result.attempts.keys()):
        attempt = result.attempts[attempt_id]

        for retry in attempt.retries:
            if retry.status == "running":
                result.is_running = True

        # Only check the latest retry
        if attempt.retries:
            last_retry = attempt.retries[-1]
            if last_retry.judge_result == "CORRECT":
                attempt.passed = True
                attempt.passed_at_retry = last_retry.retry_id
                attempt.final_status = "completed"
                attempt.final_judge_result = "CORRECT"

                if result.passed_at_attempt is None:
                    result.passed_at_attempt = attempt_id
                    result.passed_at_retry = last_retry.retry_id
                    result.final_status = "completed"
                    result.final_judge_result = "CORRECT"
            else:
                attempt.final_status = last_retry.status
                attempt.final_judge_result = last_retry.judge_result

    if result.passed_at_attempt is None and result.attempts:
        last_attempt_id = max(result.attempts.keys())
        last_attempt = result.attempts[last_attempt_id]
        result.final_status = last_attempt.final_status
        result.final_judge_result = last_attempt.final_judge_result

    return result


def _analyze_task_wrapper(args: Tuple[str, List[Path]]) -> TaskResult:
    """Wrapper for parallel processing."""
    task_id, attempt_files = args
    return analyze_task_attempts(task_id, attempt_files)


def analyze_run(task_files: Dict[str, List[Path]], parallel: bool = True) -> RunStats:
    """Analyze all tasks for a single run."""
    stats = RunStats(total_tasks=len(task_files))

    if parallel and len(task_files) > 10:
        with ProcessPoolExecutor(max_workers=8) as executor:
            task_results = list(executor.map(_analyze_task_wrapper, task_files.items()))
    else:
        task_results = [
            analyze_task_attempts(task_id, files)
            for task_id, files in task_files.items()
        ]

    for task_result in task_results:
        task_id = task_result.task_id
        stats.total_attempts += len(task_result.attempts)
        stats.total_retries += task_result.total_retries

        # Track time bounds
        if task_result.earliest_start:
            if (
                stats.earliest_start is None
                or task_result.earliest_start < stats.earliest_start
            ):
                stats.earliest_start = task_result.earliest_start
        if task_result.latest_end:
            if stats.latest_end is None or task_result.latest_end > stats.latest_end:
                stats.latest_end = task_result.latest_end

        if task_result.is_running:
            stats.running += 1
            stats.running_tasks.append(task_id)
            continue

        if task_result.passed_at_attempt is not None:
            stats.correct += 1
            stats.completed += 1

            attempt_id = task_result.passed_at_attempt
            retry_id = task_result.passed_at_retry or 0

            stats.correct_tasks.append(
                f"{task_id} (attempt@{attempt_id}, retry@{retry_id})"
            )

            if attempt_id == 1:
                stats.pass_at_1 += 1
            elif attempt_id == 2:
                stats.pass_at_2 += 1
            elif attempt_id == 3:
                stats.pass_at_3 += 1
            else:
                stats.pass_at_higher += 1
        else:
            if task_result.final_status == "completed":
                stats.completed += 1
                if task_result.final_judge_result == "INCORRECT":
                    stats.incorrect += 1
                    stats.incorrect_tasks.append(task_id)
                elif task_result.final_judge_result == "NOT_ATTEMPTED":
                    stats.not_attempted += 1
                    stats.not_attempted_tasks.append(task_id)
                else:
                    stats.incorrect += 1
                    stats.incorrect_tasks.append(task_id)
            elif task_result.final_status == "failed":
                stats.failed += 1
                stats.failed_tasks.append(task_id)
            else:
                stats.other += 1
                stats.other_tasks.append(
                    f"{task_id} (status={task_result.final_status})"
                )

    return stats


def display_run_summary(run_id: str, stats: RunStats) -> None:
    """Display summary for a single run."""
    if stats.total_tasks == 0:
        print(f"  {run_id}: No tasks found")
        return

    accuracy_bar = create_progress_bar(stats.accuracy)
    print(
        f"  [{run_id}] {stats.completed} done, {stats.running} run, {stats.failed} fail | "
        f"Acc: {stats.correct}/{stats.completed} {accuracy_bar}"
    )


def display_overall_summary(all_results: Dict[str, RunStats], num_runs: int) -> None:
    """Display overall summary across all runs."""
    totals = RunStats()
    all_correct = []
    all_incorrect = []
    all_not_attempted = []
    all_failed = []
    all_other = []
    all_running = []

    # Aggregate all stats
    for run_id in sorted(all_results.keys(), key=lambda x: int(x.split("_")[1])):
        stats = all_results[run_id]
        totals.total_tasks += stats.total_tasks
        totals.total_attempts += stats.total_attempts
        totals.total_retries += stats.total_retries
        totals.completed += stats.completed
        totals.running += stats.running
        totals.correct += stats.correct
        totals.incorrect += stats.incorrect
        totals.not_attempted += stats.not_attempted
        totals.failed += stats.failed
        totals.other += stats.other
        totals.pass_at_1 += stats.pass_at_1
        totals.pass_at_2 += stats.pass_at_2
        totals.pass_at_3 += stats.pass_at_3
        totals.pass_at_higher += stats.pass_at_higher

        # Track time bounds
        if stats.earliest_start:
            if (
                totals.earliest_start is None
                or stats.earliest_start < totals.earliest_start
            ):
                totals.earliest_start = stats.earliest_start
        if stats.latest_end:
            if totals.latest_end is None or stats.latest_end > totals.latest_end:
                totals.latest_end = stats.latest_end

        for task in stats.correct_tasks:
            all_correct.append(f"{run_id}: {task}")
        for task in stats.incorrect_tasks:
            all_incorrect.append(f"{run_id}: {task}")
        for task in stats.not_attempted_tasks:
            all_not_attempted.append(f"{run_id}: {task}")
        for task in stats.failed_tasks:
            all_failed.append(f"{run_id}: {task}")
        for task in stats.other_tasks:
            all_other.append(f"{run_id}: {task}")
        for task in stats.running_tasks:
            all_running.append(f"{run_id}: {task}")

    # Calculate expected total tasks
    expected_total = TASKS_PER_RUN * num_runs
    remaining_tasks = expected_total - totals.completed - totals.running

    # Header
    print()
    print("=" * 80)
    print(f"BROWSECOMP-ZH PROGRESS SUMMARY ({TASKS_PER_RUN} tasks)")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Overall statistics (details at top)
    print()
    print("OVERALL STATISTICS:")
    print(f"  Expected Total:     {expected_total} ({TASKS_PER_RUN} x {num_runs} runs)")
    print(f"  Completed:          {totals.completed}")
    print(f"  Running:            {totals.running}")
    print(f"  Remaining:          {remaining_tasks}")

    # Task lists
    def print_task_list(title: str, tasks: List[str], symbol: str, max_show: int = 10):
        if not tasks:
            return
        print()
        print(f"{title} ({len(tasks)}):")
        for task in tasks[:max_show]:
            print(f"  {symbol} {task}")
        if len(tasks) > max_show:
            print(f"  ... and {len(tasks) - max_show} more")

    print_task_list("FAILED TASKS", all_failed, "⚠")
    print_task_list("OTHER TASKS", all_other, "?")
    print_task_list("NOT ATTEMPTED TASKS", all_not_attempted, "⊘")
    print_task_list("INCORRECT TASKS", all_incorrect, "✗", max_show=5)

    # === Bottom section ===
    print()
    print("=" * 80)

    # Per-run breakdown
    print("PER-RUN BREAKDOWN:")
    print("-" * 80)
    for run_id in sorted(all_results.keys(), key=lambda x: int(x.split("_")[1])):
        display_run_summary(run_id, all_results[run_id])

    # Time estimation
    print("TIME ESTIMATION:")
    if totals.earliest_start and totals.latest_end and totals.completed > 0:
        elapsed = totals.latest_end - totals.earliest_start
        elapsed_minutes = elapsed.total_seconds() / 60

        # Average time per task
        avg_minutes_per_task = elapsed_minutes / totals.completed
        tasks_per_minute = (
            totals.completed / elapsed_minutes if elapsed_minutes > 0 else 0
        )

        print(f"  Elapsed Time:       {format_duration(elapsed_minutes)}")
        print(f"  Completion Rate:    {tasks_per_minute:.2f} tasks/min")
        print(f"  Avg Time/Task:      {avg_minutes_per_task:.1f} min")

        # Estimate remaining time
        if remaining_tasks > 0:
            estimated_remaining = remaining_tasks * avg_minutes_per_task
            print(f"  Est. Remaining:     ~{format_duration(estimated_remaining)}")
        else:
            print("  Est. Remaining:     All tasks completed!")
    else:
        print("  Cannot estimate (no completed tasks with timing data)")

    # Overall Accuracy
    print()
    if totals.completed > 0:
        accuracy = totals.correct / totals.completed * 100
        accuracy_bar = create_progress_bar(accuracy)
        print(f"OVERALL ACCURACY: {totals.correct}/{totals.completed} {accuracy_bar}")
    else:
        print("OVERALL ACCURACY: 0/0 (no completed tasks)")

    print()
    print("=" * 80)


def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(
        description="BrowseComp-ZH Progress Checker (289 tasks with time estimation)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python check_progress_browsecomp-zh.py logs/browsecomp-zh/xxx
        """,
    )
    parser.add_argument(
        "log_folder",
        nargs="?",
        default="logs/browsecomp-zh",
        help="Path to the log folder (default: logs/browsecomp-zh)",
    )

    args = parser.parse_args()
    log_folder = Path(args.log_folder)

    print(f"Analyzing: {log_folder}")

    if not log_folder.exists():
        print(f"Error: Log folder not found: {log_folder}")
        return 1

    runs = find_task_files(log_folder)

    if not runs:
        print(f"No task files found in {log_folder}")
        print(
            "Expected: log_folder/run_N/task_*_attempt_*_retry_*.json "
            "or task_*_attempt_*.json"
        )
        return 1

    all_results = {}
    for run_id, task_files in runs.items():
        all_results[run_id] = analyze_run(task_files)

    display_overall_summary(all_results, num_runs=len(runs))

    return 0


if __name__ == "__main__":
    sys.exit(main())
