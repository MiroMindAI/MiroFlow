#!/usr/bin/env python3
"""
GAIA Validation Text-Only Progress Checker

This script analyzes GAIA validation results in a log folder to count:
- Total tasks per run
- Tasks with status "completed"
- Tasks with judge_result "CORRECT" / "INCORRECT" / "NOT_ATTEMPTED"

Usage:
    python check_gaia_validation_text_progress.py [LOG_FOLDER_PATH]

If no path is provided, uses the default folder.

Example:
    python check_gaia_validation_text_progress.py logs/gaia-validation-text-only/binwang_agent_gaia-validation-text-only_mirothinker_single_agent_20260123_1138
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Tuple, Any


def find_task_files(log_folder: Path) -> Dict[str, List[Path]]:
    """
    Find all task JSON files grouped by run number.
    
    Args:
        log_folder: Path to the main log folder
        
    Returns:
        Dictionary mapping run_id to list of task file paths
    """
    runs = defaultdict(list)
    
    # Find all task_*_attempt_*.json files (excluding task_root_*)
    for json_file in log_folder.rglob("task_*_attempt_*.json"):
        if "task_root" in json_file.name:
            continue
            
        # Extract run number from path
        # Path structure: log_folder/run_N/subfolder/task_*.json
        parts = json_file.parts
        for part in parts:
            if part.startswith("run_") and part[4:].isdigit():
                run_id = part
                runs[run_id].append(json_file)
                break
    
    return dict(runs)


def analyze_run(task_files: List[Path]) -> Dict[str, Any]:
    """
    Analyze task files for a single run.
    
    Args:
        task_files: List of task JSON file paths
        
    Returns:
        Dictionary with analysis results
    """
    results = {
        "total": 0,
        "completed": 0,
        "running": 0,
        "pending": 0,
        "error": 0,
        "correct": 0,
        "incorrect": 0,
        "not_attempted": 0,
        "no_judge": 0,
        "parse_errors": 0,
        "correct_tasks": [],
        "incorrect_tasks": [],
    }
    
    for json_file in task_files:
        results["total"] += 1
        
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            task_meta = data.get("task_meta", {})
            status = task_meta.get("status", "").lower()
            judge_result = task_meta.get("judge_result", "").upper()
            task_id = task_meta.get("task_id", json_file.stem)
            
            # Count by status
            if status == "completed":
                results["completed"] += 1
            elif status == "running":
                results["running"] += 1
            elif status == "pending":
                results["pending"] += 1
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
                elif judge_result == "" or judge_result is None:
                    results["no_judge"] += 1
                    
        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            results["parse_errors"] += 1
    
    return results


def display_run_summary(run_id: str, results: Dict[str, Any]) -> None:
    """Display summary for a single run."""
    total = results["total"]
    completed = results["completed"]
    correct = results["correct"]
    incorrect = results["incorrect"]
    not_attempted = results["not_attempted"]
    
    if total == 0:
        print(f"  {run_id}: No tasks found")
        return
    
    # Calculate accuracy (correct / (correct + incorrect))
    judged = correct + incorrect
    accuracy = (correct / judged * 100) if judged > 0 else 0
    
    # Progress percentage
    progress = completed / total * 100
    
    print(f"  {run_id}: {completed}/{total} completed ({progress:.0f}%) | "
          f"Correct: {correct}, Incorrect: {incorrect}, Not Attempted: {not_attempted} | "
          f"Accuracy: {accuracy:.1f}%")


def display_overall_summary(all_results: Dict[str, Dict[str, Any]]) -> None:
    """Display overall summary across all runs."""
    print("\n" + "=" * 80)
    print("GAIA VALIDATION TEXT-ONLY PROGRESS SUMMARY")
    print("=" * 80)
    
    # Aggregate totals
    total_tasks = 0
    total_completed = 0
    total_running = 0
    total_pending = 0
    total_correct = 0
    total_incorrect = 0
    total_not_attempted = 0
    
    # Per-run summary
    print("\nPer-Run Summary:")
    print("-" * 80)
    
    for run_id in sorted(all_results.keys(), key=lambda x: int(x.split("_")[1])):
        results = all_results[run_id]
        display_run_summary(run_id, results)
        
        total_tasks += results["total"]
        total_completed += results["completed"]
        total_running += results["running"]
        total_pending += results["pending"]
        total_correct += results["correct"]
        total_incorrect += results["incorrect"]
        total_not_attempted += results["not_attempted"]
    
    # Overall summary
    print("-" * 80)
    print("\nOverall Statistics:")
    print(f"  Total Runs:        {len(all_results)}")
    print(f"  Total Tasks:       {total_tasks}")
    print(f"  Completed:         {total_completed} ({total_completed/total_tasks*100:.1f}%)" if total_tasks > 0 else "  Completed:         0")
    print(f"  Running:           {total_running}")
    print(f"  Pending:           {total_pending}")
    
    print("\nJudge Results (for completed tasks):")
    print(f"  CORRECT:           {total_correct}")
    print(f"  INCORRECT:         {total_incorrect}")
    print(f"  NOT_ATTEMPTED:     {total_not_attempted}")
    
    judged = total_correct + total_incorrect
    if judged > 0:
        accuracy = total_correct / judged * 100
        print(f"\nAccuracy (CORRECT / (CORRECT + INCORRECT)): {total_correct}/{judged} = {accuracy:.1f}%")
    
    if total_completed > 0:
        pass_rate = total_correct / total_completed * 100
        print(f"Pass Rate (CORRECT / Completed): {total_correct}/{total_completed} = {pass_rate:.1f}%")
    
    print("=" * 80)


def main():
    """Main function to run the analysis."""
    
    # Default folder path
    default_folder = "logs/gaia-validation-text-only"
    
    # Check if folder path was provided as command line argument
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
    
    # Find all task files grouped by run
    runs = find_task_files(log_folder)
    
    if not runs:
        print(f"No task files found in {log_folder}")
        print("Expected structure: log_folder/run_N/subfolder/task_*_attempt_*.json")
        return 1
    
    # Analyze each run
    all_results = {}
    for run_id, task_files in runs.items():
        all_results[run_id] = analyze_run(task_files)
    
    # Display results
    display_overall_summary(all_results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
