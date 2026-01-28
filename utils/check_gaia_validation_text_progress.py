#!/usr/bin/env python3
"""
GAIA Validation Text-Only Progress Checker (Pass@k Mode)

This script analyzes GAIA validation results with support for pass@k evaluation:
- Groups multiple attempts per task
- Shows pass@1, pass@2, pass@3 breakdown
- Displays: Correct | Incorrect | Not Attempted | Failed

Usage:
    python check_gaia_validation_text_progress.py [LOG_FOLDER_PATH]

Example:
    python check_gaia_validation_text_progress.py logs/gaia-validation-text-only/xxx_20260127_1654
"""

import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Progress bar configuration
PROGRESS_BAR_WIDTH = 20
GREEN_THRESHOLD = 80
YELLOW_THRESHOLD = 60
ORANGE_THRESHOLD = 40


def create_progress_bar(percentage: float, width: int = PROGRESS_BAR_WIDTH) -> str:
    """Create a visual progress bar for percentage display."""
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)

    if percentage >= GREEN_THRESHOLD:
        color = "\033[92m"  # Green
    elif percentage >= YELLOW_THRESHOLD:
        color = "\033[93m"  # Yellow
    elif percentage >= ORANGE_THRESHOLD:
        color = "\033[33m"  # Orange
    else:
        color = "\033[91m"  # Red

    reset = "\033[0m"
    return f"{color}[{bar}] {percentage:.1f}%{reset}"


def parse_task_filename(filename: str) -> Optional[Tuple[str, int]]:
    """Parse task filename to extract task_id and attempt_id."""
    match = re.match(r"task_(.+)_attempt_(\d+)\.json$", filename)
    if match:
        return match.group(1), int(match.group(2))
    return None


@dataclass
class TaskResult:
    """Result for a single task across all attempts."""

    task_id: str
    attempts: List[Dict[str, Any]] = field(default_factory=list)
    passed_at: Optional[int] = None
    final_status: str = "unknown"
    final_judge_result: str = ""
    used_exceed_max_turn_summary: bool = False
    has_valid_box: bool = False
    is_running: bool = False


@dataclass
class RunStats:
    """Statistics for a single run."""

    total_tasks: int = 0
    total_attempts: int = 0

    # Task status counts
    running: int = 0
    completed: int = 0

    # Judge result counts (4 categories)
    correct: int = 0
    incorrect: int = 0
    not_attempted: int = 0
    failed: int = 0

    # Pass@k breakdown
    pass_at_1: int = 0
    pass_at_2: int = 0
    pass_at_3: int = 0
    pass_at_higher: int = 0

    # Feature usage
    used_exceed_max_turn_summary: int = 0
    has_valid_box: int = 0

    # Task lists
    correct_tasks: List[str] = field(default_factory=list)
    incorrect_tasks: List[str] = field(default_factory=list)
    not_attempted_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    running_tasks: List[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        """Calculate accuracy: correct / completed (not_attempted counts as incorrect)."""
        return (self.correct / self.completed * 100) if self.completed > 0 else 0.0


def find_task_files(log_folder: Path) -> Dict[str, Dict[str, List[Path]]]:
    """Find all task JSON files grouped by run and task_id."""
    runs: Dict[str, Dict[str, List[Path]]] = defaultdict(lambda: defaultdict(list))

    for json_file in log_folder.rglob("task_*_attempt_*.json"):
        if "task_root" in json_file.name:
            continue

        parsed = parse_task_filename(json_file.name)
        if not parsed:
            continue

        task_id, _ = parsed

        for part in json_file.parts:
            if part.startswith("run_") and part[4:].isdigit():
                runs[part][task_id].append(json_file)
                break

    return {run_id: dict(tasks) for run_id, tasks in runs.items()}


def load_attempt_data(file_path: Path) -> Optional[Dict[str, Any]]:
    """Load and parse a single attempt JSON file."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError, OSError):
        return None


def analyze_task_attempts(task_id: str, attempt_files: List[Path]) -> TaskResult:
    """Analyze all attempts for a single task."""
    result = TaskResult(task_id=task_id)

    for file_path in attempt_files:
        parsed = parse_task_filename(file_path.name)
        if not parsed:
            continue

        _, attempt_id = parsed
        data = load_attempt_data(file_path)
        if not data:
            continue

        task_meta = data.get("task_meta", {})
        attempt = {
            "attempt_id": attempt_id,
            "status": task_meta.get("status", "").lower(),
            "judge_result": task_meta.get("judge_result", "").upper(),
            "is_valid_box": task_meta.get("is_valid_box"),
            "final_boxed_answer": task_meta.get("final_boxed_answer", ""),
            "exceed_max_turn_summary": task_meta.get("exceed_max_turn_summary"),
            "retry_with_experience": task_meta.get("retry_with_experience", False),
            "error": task_meta.get("error"),
        }
        result.attempts.append(attempt)

    result.attempts.sort(key=lambda x: x["attempt_id"])

    for attempt in result.attempts:
        if attempt["status"] == "running":
            result.is_running = True

        if attempt["retry_with_experience"]:
            result.used_exceed_max_turn_summary = True

        if attempt["is_valid_box"]:
            result.has_valid_box = True

        if attempt["judge_result"] == "CORRECT" and result.passed_at is None:
            result.passed_at = attempt["attempt_id"]
            result.final_status = "completed"
            result.final_judge_result = "CORRECT"

    if result.passed_at is None and result.attempts:
        last_attempt = result.attempts[-1]
        result.final_status = last_attempt["status"]
        result.final_judge_result = last_attempt["judge_result"]

    return result


def analyze_run(task_files: Dict[str, List[Path]]) -> RunStats:
    """Analyze all tasks for a single run."""
    stats = RunStats(total_tasks=len(task_files))

    for task_id, attempt_files in task_files.items():
        task_result = analyze_task_attempts(task_id, attempt_files)
        stats.total_attempts += len(task_result.attempts)

        if task_result.is_running:
            stats.running += 1
            stats.running_tasks.append(task_id)
            continue

        if task_result.used_exceed_max_turn_summary:
            stats.used_exceed_max_turn_summary += 1

        if task_result.has_valid_box:
            stats.has_valid_box += 1

        if task_result.passed_at is not None:
            # Correct
            stats.correct += 1
            stats.completed += 1
            stats.correct_tasks.append(f"{task_id} (pass@{task_result.passed_at})")

            if task_result.passed_at == 1:
                stats.pass_at_1 += 1
            elif task_result.passed_at == 2:
                stats.pass_at_2 += 1
            elif task_result.passed_at == 3:
                stats.pass_at_3 += 1
            else:
                stats.pass_at_higher += 1
        else:
            # Not passed - categorize by final result
            if task_result.final_status == "completed":
                stats.completed += 1
                if task_result.final_judge_result == "INCORRECT":
                    stats.incorrect += 1
                    stats.incorrect_tasks.append(task_id)
                elif task_result.final_judge_result == "NOT_ATTEMPTED":
                    stats.not_attempted += 1
                    stats.not_attempted_tasks.append(task_id)
                else:
                    # Other completed but not correct
                    stats.incorrect += 1
                    stats.incorrect_tasks.append(task_id)
            elif task_result.final_status == "failed":
                stats.failed += 1
                stats.failed_tasks.append(task_id)
            else:
                # Unknown status, count as failed
                stats.failed += 1
                stats.failed_tasks.append(task_id)

    return stats


def display_run_summary(run_id: str, stats: RunStats) -> None:
    """Display summary for a single run."""
    if stats.total_tasks == 0:
        print(f"  {run_id}: No tasks found")
        return

    # Progress bar for accuracy
    accuracy_bar = create_progress_bar(stats.accuracy)

    print(f"[{run_id}]")
    print(
        f"  Status: {stats.completed} completed | {stats.running} running | "
        f"{stats.failed} failed"
    )
    print(
        f"  Results: ✓ {stats.correct} correct | ✗ {stats.incorrect} incorrect | "
        f"⊘ {stats.not_attempted} not_attempted | ⚠ {stats.failed} failed"
    )
    print(
        f"  Pass@k: @1={stats.pass_at_1} | @2={stats.pass_at_2} | @3={stats.pass_at_3}"
    )
    print(f"  Accuracy: {stats.correct}/{stats.completed} {accuracy_bar}")
    print(
        f"  Features: exceed_summary={stats.used_exceed_max_turn_summary} | "
        f"valid_box={stats.has_valid_box}"
    )
    print()


def display_overall_summary(all_results: Dict[str, RunStats]) -> None:
    """Display overall summary across all runs."""
    print()
    print("=" * 80)
    print("GAIA VALIDATION PROGRESS SUMMARY (Pass@k Mode)")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    # Per-run summary
    print("PER-RUN BREAKDOWN:")
    print("-" * 80)

    totals = RunStats()
    all_correct = []
    all_incorrect = []
    all_not_attempted = []
    all_failed = []
    all_running = []

    for run_id in sorted(all_results.keys(), key=lambda x: int(x.split("_")[1])):
        stats = all_results[run_id]
        display_run_summary(run_id, stats)

        totals.total_tasks += stats.total_tasks
        totals.total_attempts += stats.total_attempts
        totals.completed += stats.completed
        totals.running += stats.running
        totals.correct += stats.correct
        totals.incorrect += stats.incorrect
        totals.not_attempted += stats.not_attempted
        totals.failed += stats.failed
        totals.pass_at_1 += stats.pass_at_1
        totals.pass_at_2 += stats.pass_at_2
        totals.pass_at_3 += stats.pass_at_3
        totals.pass_at_higher += stats.pass_at_higher
        totals.used_exceed_max_turn_summary += stats.used_exceed_max_turn_summary
        totals.has_valid_box += stats.has_valid_box

        for task in stats.correct_tasks:
            all_correct.append(f"{run_id}: {task}")
        for task in stats.incorrect_tasks:
            all_incorrect.append(f"{run_id}: {task}")
        for task in stats.not_attempted_tasks:
            all_not_attempted.append(f"{run_id}: {task}")
        for task in stats.failed_tasks:
            all_failed.append(f"{run_id}: {task}")
        for task in stats.running_tasks:
            all_running.append(f"{run_id}: {task}")

    # Overall summary
    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)

    print(f"Total Runs:           {len(all_results)}")
    print(f"Total Unique Tasks:   {totals.total_tasks}")
    print(f"Total Attempts:       {totals.total_attempts}")
    if totals.total_tasks > 0:
        print(f"Avg Attempts/Task:    {totals.total_attempts / totals.total_tasks:.2f}")

    print()
    print("TASK STATUS:")
    if totals.total_tasks > 0:
        completion_pct = totals.completed / totals.total_tasks * 100
        print(f"  Completed:          {totals.completed} ({completion_pct:.1f}%)")
    else:
        print(f"  Completed:          {totals.completed}")
    print(f"  Running:            {totals.running}")

    print()
    print("JUDGE RESULTS (4 categories):")
    print(f"  ✓ Correct:          {totals.correct}")
    print(f"  ✗ Incorrect:        {totals.incorrect}")
    print(f"  ⊘ Not Attempted:    {totals.not_attempted}")
    print(f"  ⚠ Failed:           {totals.failed}")

    print()
    print("PASS@K BREAKDOWN:")
    print(f"  Pass@1:             {totals.pass_at_1}")
    print(f"  Pass@2:             {totals.pass_at_2}")
    print(f"  Pass@3:             {totals.pass_at_3}")
    if totals.pass_at_higher > 0:
        print(f"  Pass@4+:            {totals.pass_at_higher}")
    print(f"  Total Passed:       {totals.correct}")

    print()
    print("FEATURE USAGE:")
    print(f"  Used Exceed Summary: {totals.used_exceed_max_turn_summary}")
    print(f"  Has Valid Box:      {totals.has_valid_box}")

    # Final accuracy with progress bar
    if totals.completed > 0:
        accuracy = totals.correct / totals.completed * 100
        accuracy_bar = create_progress_bar(accuracy)
        print()
        print(f"OVERALL ACCURACY: {totals.correct}/{totals.completed} {accuracy_bar}")

    # Task lists (limited display)
    def print_task_list(title: str, tasks: List[str], symbol: str, max_show: int = 10):
        if not tasks:
            return
        print()
        print(f"{title} ({len(tasks)}):")
        for task in tasks[:max_show]:
            print(f"  {symbol} {task}")
        if len(tasks) > max_show:
            print(f"  ... and {len(tasks) - max_show} more")

    print_task_list("RUNNING TASKS", all_running, "⏳")
    print_task_list("FAILED TASKS", all_failed, "⚠")
    print_task_list("NOT ATTEMPTED TASKS", all_not_attempted, "⊘")
    print_task_list("INCORRECT TASKS", all_incorrect, "✗", max_show=5)

    print()
    print("=" * 80)


def main():
    """Main function to run the analysis."""
    default_folder = "logs/gaia-validation-text-only"

    if len(sys.argv) > 1:
        log_folder = Path(sys.argv[1])
        print(f"Analyzing: {log_folder}")
    else:
        log_folder = Path(default_folder)
        print(f"No folder path provided, using default: {log_folder}")
        print("Usage: python check_gaia_validation_text_progress.py [LOG_FOLDER_PATH]")

    if not log_folder.exists():
        print(f"Error: Log folder not found: {log_folder}")
        return 1

    runs = find_task_files(log_folder)

    if not runs:
        print(f"No task files found in {log_folder}")
        print("Expected structure: log_folder/run_N/task_*_attempt_*.json")
        return 1

    all_results = {}
    for run_id, task_files in runs.items():
        all_results[run_id] = analyze_run(task_files)

    display_overall_summary(all_results)

    return 0


if __name__ == "__main__":
    sys.exit(main())
