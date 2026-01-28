#!/usr/bin/env python3
"""
GAIA Validation Text-Only Progress Checker

This script analyzes GAIA validation results in a log folder to count:
- Total tasks per run
- Tasks with status "completed"
- Tasks with judge_result "CORRECT" / "INCORRECT" / "NOT_ATTEMPTED"

Usage:
    python check_gaia_validation_text_progress.py [LOG_FOLDER_PATH] [--detail]

Options:
    --detail    Show detailed task IDs for failed/incorrect/not_attempted tasks

If no path is provided, uses the default folder.

Example:
    python check_gaia_validation_text_progress.py logs/gaia-validation-text-only/xxx
    python check_gaia_validation_text_progress.py logs/gaia-validation-text-only/xxx --detail
"""

import argparse
import json
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Progress bar configuration
PROGRESS_BAR_WIDTH = 20
GREEN_THRESHOLD = 80
YELLOW_THRESHOLD = 60
ORANGE_THRESHOLD = 40


def create_progress_bar(percentage: float, width: int = PROGRESS_BAR_WIDTH) -> str:
    """Create a visual progress bar for percentage display"""
    filled = int(width * percentage / 100)
    bar = "█" * filled + "░" * (width - filled)

    # Add color based on percentage
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


def find_task_files(log_folder: Path) -> Dict[str, List[Path]]:
    """
    Find all task JSON files grouped by run number.

    Args:
        log_folder: Path to the main log folder

    Returns:
        Dictionary mapping run_id to list of task file paths
    """
    runs = defaultdict(list)

    print("Scanning for task files...", end="", flush=True)
    file_count = 0

    # Find all task_*_attempt_*.json files (excluding task_root_*)
    for json_file in log_folder.rglob("task_*_attempt_*.json"):
        if "task_root" in json_file.name:
            continue

        file_count += 1

        # Extract run number from path
        # Path structure: log_folder/run_N/subfolder/task_*.json
        parts = json_file.parts
        for part in parts:
            if part.startswith("run_") and part[4:].isdigit():
                run_id = part
                runs[run_id].append(json_file)
                break

    print(f" found {file_count} files in {len(runs)} runs")
    return dict(runs)


def calculate_turns(data: Dict) -> int:
    """Calculate number of turns from task data (excluding system prompt)"""
    try:
        # Path: agent_states.main_agent.state.message_history
        agent_states = data.get("agent_states", {})
        main_agent = agent_states.get("main_agent", {})
        state = main_agent.get("state", {})
        message_history = state.get("message_history", [])

        if not message_history:
            return 0

        # Filter out system messages and count total messages, then divide by 2
        non_system_messages = [
            msg for msg in message_history if msg.get("role") != "system"
        ]

        # Each turn consists of user + assistant, so divide by 2
        turn_count = len(non_system_messages) // 2
        return turn_count
    except (KeyError, TypeError, IndexError):
        return 0


def calculate_tool_calls(data: Dict) -> Tuple[int, Dict[str, int]]:
    """
    Calculate total number of tool calls and breakdown by tool name.

    Returns:
        Tuple of (total_tool_calls, tool_call_breakdown_dict)
    """
    try:
        # Path: agent_states.main_agent.state.message_history
        agent_states = data.get("agent_states", {})
        main_agent = agent_states.get("main_agent", {})
        state = main_agent.get("state", {})
        message_history = state.get("message_history", [])

        if not message_history:
            return 0, {}

        total_tool_calls = 0
        tool_breakdown = defaultdict(int)

        for msg in message_history:
            # Check assistant messages for tool_calls field
            if msg.get("role") == "assistant":
                # Method 1: Check tool_calls array (OpenAI format)
                tool_calls = msg.get("tool_calls", [])
                if tool_calls:
                    for tc in tool_calls:
                        total_tool_calls += 1
                        # Extract tool name
                        func = tc.get("function", {})
                        tool_name = func.get("name", "unknown")
                        tool_breakdown[tool_name] += 1

                # Method 2: Check content for MCP tool call XML format
                content = msg.get("content", "")
                if isinstance(content, str) and "<use_mcp_tool>" in content:
                    # Count occurrences of <use_mcp_tool> tags
                    import re

                    mcp_calls = re.findall(r"<tool_name>(.*?)</tool_name>", content)
                    for tool_name in mcp_calls:
                        total_tool_calls += 1
                        tool_breakdown[tool_name.strip()] += 1

        return total_tool_calls, dict(tool_breakdown)
    except (KeyError, TypeError, IndexError):
        return 0, {}


def process_single_file(json_file: Path) -> Tuple[str, Dict[str, Any]]:
    """Process a single task file and return its results.

    Returns:
        Tuple of (task_id, result_dict)
    """
    result = {
        "status": None,
        "judge_result": None,
        "task_id": json_file.stem,
        "turns": 0,
        "tool_calls": 0,
        "tool_breakdown": {},
        "parse_error": False,
    }

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        task_meta = data.get("task_meta", {})
        result["status"] = task_meta.get("status", "").lower()
        result["judge_result"] = task_meta.get("judge_result", "").upper()
        result["task_id"] = task_meta.get("task_id", json_file.stem)

        # Only calculate turns and tool calls for completed tasks
        if result["status"] == "completed":
            result["turns"] = calculate_turns(data)
            result["tool_calls"], result["tool_breakdown"] = calculate_tool_calls(data)

    except (json.JSONDecodeError, KeyError, FileNotFoundError, OSError):
        result["parse_error"] = True

    return str(json_file), result


def analyze_run(task_files: List[Path], use_parallel: bool = True) -> Dict[str, Any]:
    """
    Analyze task files for a single run.

    Args:
        task_files: List of task JSON file paths
        use_parallel: Whether to use parallel processing

    Returns:
        Dictionary with analysis results
    """
    results = {
        "total": len(task_files),
        "completed": 0,
        "running": 0,
        "pending": 0,
        "failed": 0,
        "interrupted": 0,
        "error": 0,
        "correct": 0,
        "incorrect": 0,
        "not_attempted": 0,
        "no_judge": 0,
        "parse_errors": 0,
        "correct_tasks": [],
        "incorrect_tasks": [],
        "failed_tasks": [],
        "not_attempted_tasks": [],
        # Turn statistics
        "total_turns": 0,
        "tasks_with_turns": 0,
        # Tool call statistics
        "total_tool_calls": 0,
        "tasks_with_tool_calls": 0,
        "tool_breakdown": defaultdict(int),
    }

    # Process files in parallel for better performance
    if use_parallel and len(task_files) > 10:
        with ProcessPoolExecutor(max_workers=8) as executor:
            futures = {executor.submit(process_single_file, f): f for f in task_files}
            for future in as_completed(futures):
                try:
                    _, file_result = future.result()
                    _aggregate_file_result(results, file_result)
                except Exception:
                    results["parse_errors"] += 1
    else:
        # Sequential processing for small batches
        for json_file in task_files:
            _, file_result = process_single_file(json_file)
            _aggregate_file_result(results, file_result)

    return results


def _aggregate_file_result(
    results: Dict[str, Any], file_result: Dict[str, Any]
) -> None:
    """Aggregate a single file result into the overall results."""
    if file_result["parse_error"]:
        results["parse_errors"] += 1
        return

    status = file_result["status"]
    judge_result = file_result["judge_result"]
    task_id = file_result["task_id"]
    turns = file_result["turns"]
    tool_calls = file_result.get("tool_calls", 0)
    tool_breakdown = file_result.get("tool_breakdown", {})

    # Count by status
    if status == "completed":
        results["completed"] += 1
        if turns > 0:
            results["total_turns"] += turns
            results["tasks_with_turns"] += 1
        # Aggregate tool calls
        if tool_calls > 0:
            results["total_tool_calls"] += tool_calls
            results["tasks_with_tool_calls"] += 1
            # Aggregate tool breakdown
            for tool_name, count in tool_breakdown.items():
                results["tool_breakdown"][tool_name] += count
    elif status == "running":
        results["running"] += 1
    elif status == "pending":
        results["pending"] += 1
    elif status == "failed":
        results["failed"] += 1
        results["failed_tasks"].append(task_id)
    elif status == "interrupted":
        results["interrupted"] += 1
    elif status == "error":
        results["error"] += 1

    # Count by judge_result (only for completed tasks)
    if status == "completed":
        if judge_result == "CORRECT":
            results["correct"] += 1
            results["correct_tasks"].append(task_id)
        elif judge_result == "INCORRECT":
            results["incorrect"] += 1
            results["incorrect_tasks"].append(task_id)
        elif judge_result == "NOT_ATTEMPTED":
            results["not_attempted"] += 1
            results["not_attempted_tasks"].append(task_id)
        elif judge_result == "" or judge_result is None:
            results["no_judge"] += 1


def display_run_summary(run_id: str, results: Dict[str, Any]) -> None:
    """Display summary for a single run with progress bar, avg turns, and avg tool calls."""
    total = results["total"]
    completed = results["completed"]
    failed = results["failed"]
    correct = results["correct"]
    not_attempted = results["not_attempted"]
    total_turns = results.get("total_turns", 0)
    tasks_with_turns = results.get("tasks_with_turns", 0)
    total_tool_calls = results.get("total_tool_calls", 0)
    tasks_with_tool_calls = results.get("tasks_with_tool_calls", 0)

    if total == 0:
        print(f"  {run_id}: No tasks found")
        return

    # Calculate accuracy: correct / (completed + failed)
    # Failed tasks count as incorrect
    all_judged = completed + failed
    accuracy = (correct / all_judged * 100) if all_judged > 0 else 0

    # Calculate average turns
    avg_turns = (total_turns / tasks_with_turns) if tasks_with_turns > 0 else 0

    # Calculate average tool calls
    avg_tool_calls = (
        (total_tool_calls / tasks_with_tool_calls) if tasks_with_tool_calls > 0 else 0
    )

    # Create progress bar
    accuracy_bar = create_progress_bar(accuracy)

    # Build output line
    line = f"  {run_id}: {correct}/{all_judged} {accuracy_bar}"

    # Add avg turns and tool calls
    if avg_turns > 0:
        line += f" | Turns: {avg_turns:.1f}"
    if avg_tool_calls > 0:
        line += f" | Tools: {avg_tool_calls:.1f}"

    # Add not attempted / failed details
    details = []
    if not_attempted > 0:
        details.append(f"{not_attempted} not attempted")
    if failed > 0:
        details.append(f"{failed} failed")
    if details:
        line += f" | ({', '.join(details)})"

    print(line)


def display_overall_summary(
    all_results: Dict[str, Dict[str, Any]], detail: bool = False
) -> None:
    """Display overall summary across all runs.

    Args:
        all_results: Dictionary mapping run_id to analysis results
        detail: If True, show detailed task IDs for failed/incorrect/not_attempted tasks
    """
    print("\n" + "=" * 80)
    print("GAIA VALIDATION TEXT-ONLY PROGRESS SUMMARY")
    print("=" * 80)

    # Aggregate totals
    total_completed = 0
    total_failed = 0
    total_correct = 0
    total_turns = 0
    total_tasks_with_turns = 0
    total_tool_calls = 0
    total_tasks_with_tool_calls = 0
    overall_tool_breakdown = defaultdict(int)
    all_failed_tasks = []
    all_incorrect_tasks = []
    all_not_attempted_tasks = []

    # Per-run summary
    print("\nPer-Run Summary:")
    print("-" * 80)

    for run_id in sorted(all_results.keys(), key=lambda x: int(x.split("_")[1])):
        results = all_results[run_id]
        display_run_summary(run_id, results)

        total_completed += results["completed"]
        total_failed += results["failed"]
        total_correct += results["correct"]
        total_turns += results.get("total_turns", 0)
        total_tasks_with_turns += results.get("tasks_with_turns", 0)
        total_tool_calls += results.get("total_tool_calls", 0)
        total_tasks_with_tool_calls += results.get("tasks_with_tool_calls", 0)

        # Aggregate tool breakdown
        for tool_name, count in results.get("tool_breakdown", {}).items():
            overall_tool_breakdown[tool_name] += count

        # Collect failed, incorrect, and not_attempted tasks with run info
        for task_id in results.get("failed_tasks", []):
            all_failed_tasks.append(f"{run_id}: {task_id}")
        for task_id in results.get("incorrect_tasks", []):
            all_incorrect_tasks.append(f"{run_id}: {task_id}")
        for task_id in results.get("not_attempted_tasks", []):
            all_not_attempted_tasks.append(f"{run_id}: {task_id}")

    # Overall summary with progress bar
    print("-" * 80)

    # Accuracy: correct / (completed + failed)
    all_judged = total_completed + total_failed
    if all_judged > 0:
        accuracy = total_correct / all_judged * 100
        accuracy_bar = create_progress_bar(accuracy)
        print(f"\nOverall Accuracy: {total_correct}/{all_judged} {accuracy_bar}")

    # Overall average turns
    if total_tasks_with_turns > 0:
        overall_avg_turns = total_turns / total_tasks_with_turns
        print(f"Overall Avg Turns: {overall_avg_turns:.1f}")

    # Overall average tool calls
    if total_tasks_with_tool_calls > 0:
        overall_avg_tool_calls = total_tool_calls / total_tasks_with_tool_calls
        print(
            f"Overall Avg Tool Calls: {overall_avg_tool_calls:.1f} (Total: {total_tool_calls})"
        )

    # Display detailed task lists only when --detail is specified
    if detail:
        # Display tool breakdown
        if overall_tool_breakdown:
            print("\nTool Call Breakdown:")
            # Sort by count descending
            sorted_tools = sorted(
                overall_tool_breakdown.items(), key=lambda x: x[1], reverse=True
            )
            for tool_name, count in sorted_tools:
                print(f"  - {tool_name}: {count}")

        # Display failed tasks
        if all_failed_tasks:
            print(f"\nFailed Tasks ({len(all_failed_tasks)}):")
            for task in all_failed_tasks:
                print(f"  - {task}")

        # Display incorrect tasks
        if all_incorrect_tasks:
            print(f"\nIncorrect Tasks ({len(all_incorrect_tasks)}):")
            for task in all_incorrect_tasks:
                print(f"  - {task}")

        # Display not attempted tasks
        if all_not_attempted_tasks:
            print(f"\nNot Attempted Tasks ({len(all_not_attempted_tasks)}):")
            for task in all_not_attempted_tasks:
                print(f"  - {task}")
    else:
        # Show hint about --detail flag
        total_problem_tasks = (
            len(all_failed_tasks)
            + len(all_incorrect_tasks)
            + len(all_not_attempted_tasks)
        )
        if total_problem_tasks > 0:
            print(f"(Use --detail to see {total_problem_tasks} problem task IDs)")

    print("=" * 80)


def main():
    """Main function to run the analysis."""

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="GAIA Validation Text-Only Progress Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example:
    python check_gaia_validation_text_progress.py logs/gaia-validation-text-only/xxx
    python check_gaia_validation_text_progress.py logs/gaia-validation-text-only/xxx --detail
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
        help="Show detailed task IDs for failed/incorrect/not_attempted tasks",
    )

    args = parser.parse_args()
    log_folder = Path(args.log_folder)

    print(f"Analyzing: {log_folder}")
    if args.detail:
        print("(Detailed output enabled)")

    if not log_folder.exists():
        print(f"Error: Log folder not found: {log_folder}")
        return 1

    # Find all task files grouped by run
    runs = find_task_files(log_folder)

    if not runs:
        print(f"No task files found in {log_folder}")
        print("Expected structure: log_folder/run_N/task_*_attempt_*.json")
        return 1

    # Analyze each run
    all_results = {}
    for run_id, task_files in runs.items():
        all_results[run_id] = analyze_run(task_files)

    # Display results
    display_overall_summary(all_results, detail=args.detail)

    return 0


if __name__ == "__main__":
    sys.exit(main())
