#!/usr/bin/env python3
"""
Futurex-Online Progress Checker

This script analyzes Futurex-Online benchmark results in a log folder to count:
- Total files processed
- Files with status "completed" 
- Files with predictions (final_boxed_answer)
- Files with errors

Usage:
    python check_futurex_progress.py [LOG_FOLDER_PATH]

If no path is provided, uses the current directory.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def analyze_futurex_results(log_folder: str) -> Dict[str, int]:
    """
    Analyze Futurex-Online benchmark results from JSON log files.

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
        "running_status": 0,
        "failed_status": 0,
        "with_predictions": 0,
        "without_predictions": 0,
        "with_errors": 0,
        "parse_errors": 0,
    }

    completed_files = []
    running_files = []
    failed_files = []
    prediction_files = []
    error_files = []
    parse_error_files = []

    print(f"Scanning {len(json_files)} files in {log_folder}...")

    for json_file in json_files:
        results["total_files"] += 1

        try:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            status = data.get("status", "").lower()
            final_answer = data.get("final_boxed_answer", "")
            error_msg = data.get("error", "")
            judge_result = data.get("judge_result", "")

            # Count by status
            if status == "completed":
                results["completed_status"] += 1
                completed_files.append(json_file.name)
            elif status == "running":
                results["running_status"] += 1
                running_files.append(json_file.name)
            elif status in ["failed", "error"]:
                results["failed_status"] += 1
                failed_files.append(json_file.name)
            else:
                # Unknown status
                results["failed_status"] += 1
                failed_files.append((json_file.name, f"Unknown status: {status}"))

            # Count by prediction availability
            if final_answer and final_answer.strip():
                results["with_predictions"] += 1
                prediction_files.append((json_file.name, final_answer[:100] + "..." if len(final_answer) > 100 else final_answer))
            else:
                results["without_predictions"] += 1

            # Count by error presence
            if error_msg and error_msg.strip():
                results["with_errors"] += 1
                error_files.append((json_file.name, error_msg))

        except (json.JSONDecodeError, KeyError, FileNotFoundError) as e:
            results["parse_errors"] += 1
            parse_error_files.append((json_file.name, str(e)))
            print(f"Error parsing {json_file.name}: {e}")

    return (
        results,
        completed_files,
        running_files,
        failed_files,
        prediction_files,
        error_files,
        parse_error_files,
    )


def display_results(
    results: Dict[str, int],
    completed_files: List[str],
    running_files: List[str],
    failed_files: List[str],
    prediction_files: List[Tuple[str, str]],
    error_files: List[Tuple[str, str]],
    parse_error_files: List[Tuple[str, str]],
) -> None:
    """Display the analysis results in a formatted way."""

    print("\n" + "=" * 60)
    print("FUTUREX-ONLINE BENCHMARK RESULTS SUMMARY")
    print("=" * 60)

    total = results["total_files"]
    completed = results["completed_status"]
    running = results["running_status"]
    failed = results["failed_status"]
    with_predictions = results["with_predictions"]
    with_errors = results["with_errors"]

    print(f"Total files processed:           {total:3d}")
    print(f"Files with status 'completed':   {completed:3d} ({completed/total*100:.1f}%)")
    print(f"Files with status 'running':     {running:3d} ({running/total*100:.1f}%)")
    print(f"Files with status 'failed':      {failed:3d} ({failed/total*100:.1f}%)")
    print(f"Files with predictions:          {with_predictions:3d} ({with_predictions/total*100:.1f}%)")
    print(f"Files with errors:               {with_errors:3d} ({with_errors/total*100:.1f}%)")
    print(f"Files with parse errors:         {results['parse_errors']:3d}")

    if completed > 0:
        prediction_rate = with_predictions / completed * 100
        print(f"\nPrediction rate (predictions/completed): {prediction_rate:.1f}%")

    print("\n" + "-" * 60)
    print(f"SUMMARY: {completed} tasks completed, {with_predictions} with predictions")
    print("-" * 60)

    # Show some example files for verification
    if completed_files:
        print("\nFirst 5 completed files:")
        for i, filename in enumerate(completed_files[:5], 1):
            print(f"  {i}. {filename}")
        if len(completed_files) > 5:
            print(f"  ... and {len(completed_files) - 5} more")

    if running_files:
        print("\nFirst 5 running files:")
        for i, filename in enumerate(running_files[:5], 1):
            print(f"  {i}. {filename}")
        if len(running_files) > 5:
            print(f"  ... and {len(running_files) - 5} more")

    if prediction_files:
        print("\nFirst 5 files with predictions:")
        for i, (filename, prediction) in enumerate(prediction_files[:5], 1):
            print(f"  {i}. {filename}")
            print(f"     Prediction: {prediction}")
        if len(prediction_files) > 5:
            print(f"  ... and {len(prediction_files) - 5} more")

    if error_files:
        print("\nFiles with errors:")
        for filename, error in error_files[:5]:
            print(f"  - {filename}: {error[:100]}...")
        if len(error_files) > 5:
            print(f"  ... and {len(error_files) - 5} more")

    if parse_error_files:
        print("\nFiles with parse errors:")
        for filename, error in parse_error_files:
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
        print(f"Analyzing Futurex-Online benchmark results in: {log_folder}")
        results, completed_files, running_files, failed_files, prediction_files, error_files, parse_error_files = analyze_futurex_results(
            log_folder
        )
        display_results(results, completed_files, running_files, failed_files, prediction_files, error_files, parse_error_files)

    except Exception as e:
        print(f"Error: {e}")
        print(f"\nUsage: python {sys.argv[0]} [LOG_FOLDER_PATH]")
        print(f"Example: python {sys.argv[0]} logs/futurex-online-test")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
