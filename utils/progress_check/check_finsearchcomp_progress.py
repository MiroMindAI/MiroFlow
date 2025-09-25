#!/usr/bin/env python3
"""
FinSearchComp Progress Checker

This script analyzes FinSearchComp benchmark results in a log folder to count:
- Total files processed
- Files with status "completed"
- Files with status "completed" AND judge_result "CORRECT" (excluding T1 tasks)
- Breakdown by task type (T1, T2, T3)

Note: T1 (Time-Sensitive Data Fetching) tasks are excluded from correctness evaluation
because their ground truth is outdated, but they are still counted as completed.

Usage:
    python check_finsearchcomp_progress.py [LOG_FOLDER_PATH]

If no path is provided, uses the current directory.
"""

import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def extract_task_type(task_id: str) -> str:
    """
    Extract task type (T1, T2, T3) from task_id.
    
    Args:
        task_id: Task ID string like "(T1)Time_Sensitive_Data_Fetching_006"
        
    Returns:
        Task type string ("T1", "T2", "T3", or "Unknown")
    """
    match = re.match(r'^\(T(\d+)\)', task_id)
    if match:
        return f"T{match.group(1)}"
    return "Unknown"


def extract_region_from_label(label: str) -> str:
    """
    Extract region from the label field.
    
    Args:
        label: Label string like "Complex_Historical_Investigation(Global)" or "Financial_Analysis(Greater_China)"
        
    Returns:
        Region string ("Global", "Greater China", or "Unknown")
    """
    if not label:
        return "Unknown"
    
    if "(Global)" in label:
        return "Global"
    elif "(Greater China)" in label:
        return "Greater China"
    else:
        return "Unknown"


def analyze_finsearchcomp_results(log_folder: str) -> Dict[str, any]:
    """
    Analyze FinSearchComp benchmark results from JSON log files.

    Args:
        log_folder: Path to folder containing task_*.json files

    Returns:
        Dictionary with counts of different categories
    """
    log_path = Path(log_folder)

    if not log_path.exists():
        raise FileNotFoundError(f"Log folder not found: {log_folder}")

    # Find all task JSON files
    json_files = list(log_path.glob("task_*_attempt_*.json"))

    results = {
        "total_files": 0,
        "completed_status": 0,
        "completed_and_correct": 0,
        "completed_and_incorrect": 0,
        "other_status": 0,
        "parse_errors": 0,
        "task_type_breakdown": {
            "T1": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
            "T2": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
            "T3": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
            "Unknown": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0}
        },
        "regional_breakdown": {
            "Global": {
                "T2": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                "T3": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0}
            },
            "Greater China": {
                "T2": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0},
                "T3": {"total": 0, "completed": 0, "correct": 0, "incorrect": 0}
            }
        }
    }

    completed_correct_files = []
    completed_incorrect_files = []
    parse_error_files = []

    print(f"Scanning {len(json_files)} files in {log_folder}...")

    for json_file in json_files:
        results["total_files"] += 1

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            task_id = data.get("task_id", "")
            task_type = extract_task_type(task_id)
            status = data.get("status", "").lower()
            judge_result = data.get("judge_result", "").upper()
            
            # Extract region from label
            label = data.get("input", {}).get("metadata", {}).get("label", "")
            region = extract_region_from_label(label)

            # Update task type breakdown
            results["task_type_breakdown"][task_type]["total"] += 1
            
            # Update regional breakdown for T2 and T3 tasks
            if task_type in ["T2", "T3"] and region in results["regional_breakdown"]:
                results["regional_breakdown"][region][task_type]["total"] += 1

            if status == "completed":
                results["completed_status"] += 1
                results["task_type_breakdown"][task_type]["completed"] += 1
                
                # Update regional breakdown for completed T2 and T3 tasks
                if task_type in ["T2", "T3"] and region in results["regional_breakdown"]:
                    results["regional_breakdown"][region][task_type]["completed"] += 1

                # For T1 tasks, exclude from correctness evaluation but count as completed
                if task_type == "T1":
                    # T1 tasks are considered "completed" but not evaluated for correctness
                    # due to outdated ground truth
                    pass
                else:
                    # For T2 and T3 tasks, evaluate correctness
                    if judge_result == "CORRECT":
                        results["completed_and_correct"] += 1
                        results["task_type_breakdown"][task_type]["correct"] += 1
                        # Update regional breakdown for correct T2 and T3 tasks
                        if task_type in ["T2", "T3"] and region in results["regional_breakdown"]:
                            results["regional_breakdown"][region][task_type]["correct"] += 1
                        completed_correct_files.append(json_file.name)
                    else:
                        results["completed_and_incorrect"] += 1
                        results["task_type_breakdown"][task_type]["incorrect"] += 1
                        # Update regional breakdown for incorrect T2 and T3 tasks
                        if task_type in ["T2", "T3"] and region in results["regional_breakdown"]:
                            results["regional_breakdown"][region][task_type]["incorrect"] += 1
                        completed_incorrect_files.append((json_file.name, judge_result))
            else:
                results["other_status"] += 1

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            results["parse_errors"] += 1
            parse_error_files.append((json_file.name, str(e)))
            print(f"Error parsing {json_file.name}: {e}")

    return (
        results,
        completed_correct_files,
        completed_incorrect_files,
        parse_error_files,
    )


def display_results(
    results: Dict[str, any],
    correct_files: List[str],
    incorrect_files: List[Tuple[str, str]],
    error_files: List[Tuple[str, str]],
) -> None:
    """Display the analysis results in a formatted way."""

    print("\n" + "=" * 70)
    print("FINSEARCHCOMP BENCHMARK RESULTS SUMMARY")
    print("=" * 70)

    total = results["total_files"]
    completed = results["completed_status"]
    correct = results["completed_and_correct"]
    incorrect = results["completed_and_incorrect"]

    print(f"Total files processed:           {total:3d}")
    print(
        f"Files with status 'completed':   {completed:3d} ({completed/total*100:.1f}%)"
    )
    print(f"Files completed AND correct:     {correct:3d} ({correct/total*100:.1f}%)")
    print(
        f"Files completed but incorrect:   {incorrect:3d} ({incorrect/total*100:.1f}%)"
    )
    print(f"Files with other status:         {results['other_status']:3d}")
    print(f"Files with parse errors:         {results['parse_errors']:3d}")

    # Calculate accuracy excluding T1 tasks
    t2_t3_completed = (
        results["task_type_breakdown"]["T2"]["completed"] + 
        results["task_type_breakdown"]["T3"]["completed"]
    )
    t2_t3_correct = (
        results["task_type_breakdown"]["T2"]["correct"] + 
        results["task_type_breakdown"]["T3"]["correct"]
    )
    
    if t2_t3_completed > 0:
        accuracy = t2_t3_correct / t2_t3_completed * 100
        print(f"\nAccuracy rate (T2+T3 correct/completed): {accuracy:.1f}%")
        print(f"  (T1 tasks excluded due to outdated ground truth)")

    # Task type breakdown
    print("\n" + "-" * 70)
    print("TASK TYPE BREAKDOWN")
    print("-" * 70)
    
    for task_type in ["T1", "T2", "T3", "Unknown"]:
        breakdown = results["task_type_breakdown"][task_type]
        if breakdown["total"] > 0:
            completion_rate = breakdown["completed"] / breakdown["total"] * 100
            if task_type == "T1":
                print(f"{task_type} (Time-Sensitive Data Fetching):")
                print(f"  Total: {breakdown['total']:3d}, Completed: {breakdown['completed']:3d} ({completion_rate:.1f}%)")
                print(f"  Note: Excluded from correctness evaluation (outdated ground truth)")
            else:
                accuracy_rate = breakdown["correct"] / breakdown["completed"] * 100 if breakdown["completed"] > 0 else 0
                print(f"{task_type} ({'Simple Historical Lookup' if task_type == 'T2' else 'Complex Historical Investigation'}):")
                print(f"  Total: {breakdown['total']:3d}, Completed: {breakdown['completed']:3d} ({completion_rate:.1f}%)")
                print(f"  Correct: {breakdown['correct']:3d}, Incorrect: {breakdown['incorrect']:3d}")
                print(f"  Accuracy: {accuracy_rate:.1f}%")

    # Regional breakdown for T2 and T3
    print("\n" + "-" * 70)
    print("REGIONAL BREAKDOWN (T2 & T3 TASKS)")
    print("-" * 70)
    
    for region in ["Global", "Greater China"]:
        print(f"\n{region} Region:")
        for task_type in ["T2", "T3"]:
            breakdown = results["regional_breakdown"][region][task_type]
            if breakdown["total"] > 0:
                completion_rate = breakdown["completed"] / breakdown["total"] * 100
                accuracy_rate = breakdown["correct"] / breakdown["completed"] * 100 if breakdown["completed"] > 0 else 0
                task_name = "Simple Historical Lookup" if task_type == "T2" else "Complex Historical Investigation"
                print(f"  {task_type} ({task_name}):")
                print(f"    Total: {breakdown['total']:3d}, Completed: {breakdown['completed']:3d} ({completion_rate:.1f}%)")
                print(f"    Correct: {breakdown['correct']:3d}, Incorrect: {breakdown['incorrect']:3d}")
                print(f"    Accuracy: {accuracy_rate:.1f}%")

    print("\n" + "-" * 70)
    print(f"SUMMARY: {completed} tasks completed, {correct} T2+T3 tasks correct")
    print(f"         (T1 tasks: {results['task_type_breakdown']['T1']['completed']} completed, excluded from evaluation)")
    print("-" * 70)

    # Show some example files for verification
    if correct_files:
        print("\nFirst 5 correct files (T2+T3 only):")
        for i, filename in enumerate(correct_files[:5], 1):
            print(f"  {i}. {filename}")
        if len(correct_files) > 5:
            print(f"  ... and {len(correct_files) - 5} more")

    if incorrect_files:
        print("\nFirst 5 incorrect files (T2+T3 only):")
        for i, (filename, judge_result) in enumerate(incorrect_files[:5], 1):
            print(f"  {i}. {filename} -> {judge_result}")
        if len(incorrect_files) > 5:
            print(f"  ... and {len(incorrect_files) - 5} more")

    if error_files:
        print("\nFiles with parse errors:")
        for filename, error in error_files:
            print(f"  - {filename}: {error}")


def main():
    """Main function to run the analysis."""

    # Check if folder path was provided as command line argument
    if len(sys.argv) > 1:
        log_folder = sys.argv[1]
        print(f"Using provided folder path: {log_folder}")
    else:
        log_folder = "."
        print(f"No folder path provided, using current directory: {log_folder}")

    try:
        print(f"Analyzing FinSearchComp benchmark results in: {log_folder}")
        results, correct_files, incorrect_files, error_files = analyze_finsearchcomp_results(
            log_folder
        )
        display_results(results, correct_files, incorrect_files, error_files)

    except Exception as e:
        print(f"Error: {e}")
        print(f"\nUsage: python {sys.argv[0]} [LOG_FOLDER_PATH]")
        print(f"Example: python {sys.argv[0]} logs/finsearchcomp/agent_finsearchcomp_20250924_1555")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
