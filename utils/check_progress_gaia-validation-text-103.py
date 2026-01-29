#!/usr/bin/env python3
"""
GAIA Validation Progress Checker (Full Feature Version)

This script analyzes GAIA validation results with the new naming convention:
- File format: task_{task_id}_attempt_{attempt_id}_retry_{retry_id}.json
- Groups by attempt (pass@k) and retry within each attempt
- Shows pass@1, pass@2, pass@3 breakdown
- Shows retry statistics per attempt
- Shows avg turns and avg tool calls
- Displays: Correct | Incorrect | Not Attempted | Failed

Usage:
    python fangda_check_progress_gaia_validation_text_103.py [LOG_FOLDER_PATH] [--detail]

Options:
    --detail    Show detailed task IDs and tool breakdown

Example:
    python fangda_check_progress_gaia_validation_text_103.py logs/gaia-validation-text-only/xxx
    python fangda_check_progress_gaia_validation_text_103.py logs/gaia-validation-text-only/xxx --detail
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

# Precompile regex patterns for better performance
MCP_TOOL_PATTERN = re.compile(r"<tool_name>(.*?)</tool_name>")
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
    """Parse task filename to extract task_id, attempt_id, and retry_id.

    Supports:
    - New format: task_{task_id}_attempt_{attempt_id}_retry_{retry_id}.json
    - Old format: task_{task_id}_attempt_{attempt_id}.json (retry_id = 0)
    """
    # New format (use precompiled pattern)
    match = TASK_FILENAME_NEW_PATTERN.match(filename)
    if match:
        return match.group(1), int(match.group(2)), int(match.group(3))

    # Old format fallback
    match = TASK_FILENAME_OLD_PATTERN.match(filename)
    if match:
        return match.group(1), int(match.group(2)), 0

    return None


def calculate_turns_and_tools(data: Dict) -> Tuple[int, int, Dict[str, int]]:
    """Calculate turns and tool calls in a single pass through message_history.

    Returns:
        Tuple of (turn_count, total_tool_calls, tool_breakdown)
    """
    try:
        agent_states = data.get("agent_states", {})
        main_agent = agent_states.get("main_agent", {})
        state = main_agent.get("state", {})
        message_history = state.get("message_history", [])

        if not message_history:
            return 0, 0, {}

        non_system_count = 0
        total_tool_calls = 0
        tool_breakdown = defaultdict(int)

        for msg in message_history:
            role = msg.get("role")
            if role == "system":
                continue

            non_system_count += 1

            if role == "assistant":
                # Method 1: Check tool_calls array (OpenAI format)
                tool_calls = msg.get("tool_calls")
                if tool_calls:
                    for tc in tool_calls:
                        total_tool_calls += 1
                        func = tc.get("function", {})
                        tool_name = func.get("name", "unknown")
                        tool_breakdown[tool_name] += 1

                # Method 2: Check content for MCP tool call XML format
                content = msg.get("content", "")
                if isinstance(content, str) and "<use_mcp_tool>" in content:
                    mcp_calls = MCP_TOOL_PATTERN.findall(content)
                    for tool_name in mcp_calls:
                        total_tool_calls += 1
                        tool_breakdown[tool_name.strip()] += 1

        turn_count = non_system_count // 2
        return turn_count, total_tool_calls, dict(tool_breakdown)
    except (KeyError, TypeError, IndexError):
        return 0, 0, {}


@dataclass
class RetryResult:
    """Result for a single retry within an attempt."""

    retry_id: int
    status: str = ""
    judge_result: str = ""
    is_valid_box: bool = False
    final_boxed_answer: str = ""
    exceed_max_turn_summary: Optional[str] = None
    used_exceed_max_turn_summaries: bool = False
    error: Optional[str] = None
    turns: int = 0
    tool_calls: int = 0
    tool_breakdown: Dict[str, int] = field(default_factory=dict)


@dataclass
class AttemptResult:
    """Result for a single attempt (may contain multiple retries)."""

    attempt_id: int
    retries: List[RetryResult] = field(default_factory=list)
    passed: bool = False
    passed_at_retry: Optional[int] = None
    final_status: str = ""
    final_judge_result: str = ""
    has_valid_box: bool = False


@dataclass
class TaskResult:
    """Result for a single task across all attempts and retries."""

    task_id: str
    attempts: Dict[int, AttemptResult] = field(default_factory=dict)
    passed_at_attempt: Optional[int] = None
    passed_at_retry: Optional[int] = None
    final_status: str = "unknown"
    final_judge_result: str = ""
    used_exceed_max_turn_summary: bool = False
    has_valid_box: bool = False
    is_running: bool = False
    total_retries: int = 0
    total_turns: int = 0
    total_tool_calls: int = 0
    tool_breakdown: Dict[str, int] = field(default_factory=dict)


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

    pass_at_1: int = 0
    pass_at_2: int = 0
    pass_at_3: int = 0
    pass_at_higher: int = 0

    retry_0_success: int = 0
    retry_1_success: int = 0
    retry_2_success: int = 0
    retry_higher_success: int = 0

    used_exceed_max_turn_summary: int = 0
    has_valid_box: int = 0

    # Turn and tool stats
    total_turns: int = 0
    tasks_with_turns: int = 0
    total_tool_calls: int = 0
    tasks_with_tool_calls: int = 0
    tool_breakdown: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    correct_tasks: List[str] = field(default_factory=list)
    incorrect_tasks: List[str] = field(default_factory=list)
    not_attempted_tasks: List[str] = field(default_factory=list)
    failed_tasks: List[str] = field(default_factory=list)
    running_tasks: List[str] = field(default_factory=list)

    @property
    def accuracy(self) -> float:
        return (self.correct / self.completed * 100) if self.completed > 0 else 0.0

    @property
    def avg_turns(self) -> float:
        return (
            (self.total_turns / self.tasks_with_turns)
            if self.tasks_with_turns > 0
            else 0.0
        )

    @property
    def avg_tool_calls(self) -> float:
        return (
            (self.total_tool_calls / self.tasks_with_tool_calls)
            if self.tasks_with_tool_calls > 0
            else 0.0
        )


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
    """Analyze all attempts and retries for a single task."""
    result = TaskResult(task_id=task_id)
    task_tool_breakdown = defaultdict(int)

    for file_path in attempt_files:
        parsed = parse_task_filename(file_path.name)
        if not parsed:
            continue

        _, attempt_id, retry_id = parsed
        data = load_attempt_data(file_path)
        if not data:
            continue

        task_meta = data.get("task_meta", {})

        # Calculate turns and tool calls in a single pass
        turns, tool_calls, tool_breakdown = calculate_turns_and_tools(data)

        retry = RetryResult(
            retry_id=retry_id,
            status=task_meta.get("status", "").lower(),
            judge_result=task_meta.get("judge_result", "").upper(),
            is_valid_box=task_meta.get("is_valid_box", False),
            final_boxed_answer=task_meta.get("final_boxed_answer", ""),
            exceed_max_turn_summary=task_meta.get("exceed_max_turn_summary"),
            used_exceed_max_turn_summaries=task_meta.get(
                "used_exceed_max_turn_summaries", False
            ),
            error=task_meta.get("error"),
            turns=turns,
            tool_calls=tool_calls,
            tool_breakdown=tool_breakdown,
        )

        if attempt_id not in result.attempts:
            result.attempts[attempt_id] = AttemptResult(attempt_id=attempt_id)

        result.attempts[attempt_id].retries.append(retry)
        result.total_retries += 1

        # Aggregate turns and tool calls
        if retry.status == "completed":
            result.total_turns += turns
            result.total_tool_calls += tool_calls
            for tool_name, count in tool_breakdown.items():
                task_tool_breakdown[tool_name] += count

    result.tool_breakdown = dict(task_tool_breakdown)

    for attempt in result.attempts.values():
        attempt.retries.sort(key=lambda x: x.retry_id)

    for attempt_id in sorted(result.attempts.keys()):
        attempt = result.attempts[attempt_id]

        for retry in attempt.retries:
            if retry.status == "running":
                result.is_running = True

            if retry.used_exceed_max_turn_summaries:
                result.used_exceed_max_turn_summary = True

            if retry.is_valid_box:
                attempt.has_valid_box = True
                result.has_valid_box = True

            if retry.judge_result == "CORRECT" and not attempt.passed:
                attempt.passed = True
                attempt.passed_at_retry = retry.retry_id
                attempt.final_status = "completed"
                attempt.final_judge_result = "CORRECT"

                if result.passed_at_attempt is None:
                    result.passed_at_attempt = attempt_id
                    result.passed_at_retry = retry.retry_id
                    result.final_status = "completed"
                    result.final_judge_result = "CORRECT"

        if not attempt.passed and attempt.retries:
            last_retry = attempt.retries[-1]
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

    # Use parallel processing for better performance
    if parallel and len(task_files) > 10:
        with ProcessPoolExecutor(max_workers=8) as executor:
            task_results = list(executor.map(_analyze_task_wrapper, task_files.items()))
    else:
        task_results = [
            analyze_task_attempts(task_id, attempt_files)
            for task_id, attempt_files in task_files.items()
        ]

    for task_result in task_results:
        task_id = task_result.task_id
        stats.total_attempts += len(task_result.attempts)
        stats.total_retries += task_result.total_retries

        # Aggregate turns and tool calls
        if task_result.total_turns > 0:
            stats.total_turns += task_result.total_turns
            stats.tasks_with_turns += 1
        if task_result.total_tool_calls > 0:
            stats.total_tool_calls += task_result.total_tool_calls
            stats.tasks_with_tool_calls += 1
            for tool_name, count in task_result.tool_breakdown.items():
                stats.tool_breakdown[tool_name] += count

        if task_result.is_running:
            stats.running += 1
            stats.running_tasks.append(task_id)
            continue

        if task_result.used_exceed_max_turn_summary:
            stats.used_exceed_max_turn_summary += 1

        if task_result.has_valid_box:
            stats.has_valid_box += 1

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

            if retry_id == 0:
                stats.retry_0_success += 1
            elif retry_id == 1:
                stats.retry_1_success += 1
            elif retry_id == 2:
                stats.retry_2_success += 1
            else:
                stats.retry_higher_success += 1
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
                stats.failed += 1
                stats.failed_tasks.append(task_id)

    return stats


def display_run_summary(run_id: str, stats: RunStats) -> None:
    """Display summary for a single run."""
    if stats.total_tasks == 0:
        print(f"  {run_id}: No tasks found")
        return

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
    print(
        f"  Retry:  @0={stats.retry_0_success} | @1={stats.retry_1_success} | "
        f"@2={stats.retry_2_success}"
    )
    print(f"  Accuracy: {stats.correct}/{stats.completed} {accuracy_bar}")

    # Turn and tool stats
    turn_info = f"Turns: {stats.avg_turns:.1f}" if stats.avg_turns > 0 else ""
    tool_info = f"Tools: {stats.avg_tool_calls:.1f}" if stats.avg_tool_calls > 0 else ""
    if turn_info or tool_info:
        parts = [p for p in [turn_info, tool_info] if p]
        print(f"  Avg: {' | '.join(parts)}")

    print(
        f"  Features: exceed_summary={stats.used_exceed_max_turn_summary} | "
        f"valid_box={stats.has_valid_box}"
    )
    print()


def display_overall_summary(
    all_results: Dict[str, RunStats], detail: bool = False
) -> None:
    """Display overall summary across all runs."""
    print()
    print("=" * 80)
    print("GAIA VALIDATION PROGRESS SUMMARY (Full Feature Version)")
    print(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    print()

    print("PER-RUN BREAKDOWN:")
    print("-" * 80)

    totals = RunStats()
    overall_tool_breakdown = defaultdict(int)
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
        totals.total_retries += stats.total_retries
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
        totals.retry_0_success += stats.retry_0_success
        totals.retry_1_success += stats.retry_1_success
        totals.retry_2_success += stats.retry_2_success
        totals.retry_higher_success += stats.retry_higher_success
        totals.used_exceed_max_turn_summary += stats.used_exceed_max_turn_summary
        totals.has_valid_box += stats.has_valid_box

        # Aggregate turn and tool stats
        totals.total_turns += stats.total_turns
        totals.tasks_with_turns += stats.tasks_with_turns
        totals.total_tool_calls += stats.total_tool_calls
        totals.tasks_with_tool_calls += stats.tasks_with_tool_calls
        for tool_name, count in stats.tool_breakdown.items():
            overall_tool_breakdown[tool_name] += count

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

    print("=" * 80)
    print("OVERALL STATISTICS")
    print("=" * 80)

    print(f"Total Runs:           {len(all_results)}")
    print(f"Total Unique Tasks:   {totals.total_tasks}")
    print(f"Total Attempts:       {totals.total_attempts}")
    print(f"Total Retries:        {totals.total_retries}")
    if totals.total_tasks > 0:
        print(f"Avg Attempts/Task:    {totals.total_attempts / totals.total_tasks:.2f}")
        print(f"Avg Retries/Task:     {totals.total_retries / totals.total_tasks:.2f}")

    print()
    print("TASK STATUS:")
    if totals.total_tasks > 0:
        completion_pct = totals.completed / totals.total_tasks * 100
        print(f"  Completed:          {totals.completed} ({completion_pct:.1f}%)")
    else:
        print(f"  Completed:          {totals.completed}")
    print(f"  Running:            {totals.running}")

    print()
    print("JUDGE RESULTS:")
    print(f"  ✓ Correct:          {totals.correct}")
    print(f"  ✗ Incorrect:        {totals.incorrect}")
    print(f"  ⊘ Not Attempted:    {totals.not_attempted}")
    print(f"  ⚠ Failed:           {totals.failed}")

    print()
    print("PASS@K BREAKDOWN (by attempt):")
    print(f"  Pass@1:             {totals.pass_at_1}")
    print(f"  Pass@2:             {totals.pass_at_2}")
    print(f"  Pass@3:             {totals.pass_at_3}")
    if totals.pass_at_higher > 0:
        print(f"  Pass@4+:            {totals.pass_at_higher}")
    print(f"  Total Passed:       {totals.correct}")

    print()
    print("RETRY BREAKDOWN (within successful attempts):")
    print(f"  Retry@0 (no retry): {totals.retry_0_success}")
    print(f"  Retry@1:            {totals.retry_1_success}")
    print(f"  Retry@2:            {totals.retry_2_success}")
    if totals.retry_higher_success > 0:
        print(f"  Retry@3+:           {totals.retry_higher_success}")

    print()
    print("TURN & TOOL STATISTICS:")
    if totals.tasks_with_turns > 0:
        print(
            f"  Avg Turns/Task:     {totals.total_turns / totals.tasks_with_turns:.1f}"
        )
    if totals.tasks_with_tool_calls > 0:
        print(
            f"  Avg Tools/Task:     {totals.total_tool_calls / totals.tasks_with_tool_calls:.1f}"
        )
    print(f"  Total Tool Calls:   {totals.total_tool_calls}")

    print()
    print("FEATURE USAGE:")
    print(f"  Used Exceed Summary: {totals.used_exceed_max_turn_summary}")
    print(f"  Has Valid Box:      {totals.has_valid_box}")

    if totals.completed > 0:
        accuracy = totals.correct / totals.completed * 100
        accuracy_bar = create_progress_bar(accuracy)
        print()
        print(f"OVERALL ACCURACY: {totals.correct}/{totals.completed} {accuracy_bar}")

    # Detailed output
    if detail:
        if overall_tool_breakdown:
            print()
            print("TOOL CALL BREAKDOWN:")
            sorted_tools = sorted(
                overall_tool_breakdown.items(), key=lambda x: x[1], reverse=True
            )
            for tool_name, count in sorted_tools:
                print(f"  - {tool_name}: {count}")

    def print_task_list(title: str, tasks: List[str], symbol: str, max_show: int = 10):
        if not tasks:
            return
        print()
        print(f"{title} ({len(tasks)}):")
        for task in tasks[:max_show]:
            print(f"  {symbol} {task}")
        if len(tasks) > max_show:
            remaining = len(tasks) - max_show
            if detail:
                for task in tasks[max_show:]:
                    print(f"  {symbol} {task}")
            else:
                print(f"  ... and {remaining} more (use --detail to show all)")

    print_task_list("RUNNING TASKS", all_running, "⏳")
    print_task_list("FAILED TASKS", all_failed, "⚠")
    print_task_list("NOT ATTEMPTED TASKS", all_not_attempted, "⊘")
    print_task_list("INCORRECT TASKS", all_incorrect, "✗", max_show=5)

    print()
    print("=" * 80)


def main():
    """Main function to run the analysis."""
    parser = argparse.ArgumentParser(
        description="GAIA Validation Progress Checker (Full Feature Version)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python fangda_check_progress_gaia_validation_text_103.py logs/gaia-validation-text-only/xxx
    python fangda_check_progress_gaia_validation_text_103.py logs/gaia-validation-text-only/xxx --detail
        """,
    )
    parser.add_argument(
        "log_folder",
        nargs="?",
        default="logs/gaia-validation-text-only",
        help="Path to the log folder (default: logs/gaia-validation-text-only)",
    )
    parser.add_argument(
        "--detail",
        action="store_true",
        help="Show detailed task IDs and tool breakdown",
    )

    args = parser.parse_args()
    log_folder = Path(args.log_folder)

    print(f"Analyzing: {log_folder}")
    if args.detail:
        print("(Detailed output enabled)")

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

    display_overall_summary(all_results, detail=args.detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
