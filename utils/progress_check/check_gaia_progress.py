#!/usr/bin/env python3
"""
GAIA Validation Progress Checker

This script analyzes GAIA validation results in a log folder to count:
- Total files processed
- Files with status "completed"
- Files with status "completed" AND judge_result "CORRECT"

Usage:
    python check_gaia_progress.py [LOG_FOLDER_PATH]

If no path is provided, uses the default folder.
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Tuple


def analyze_gaia_results(log_folder: str) -> Dict[str, int]:
    """
    Analyze GAIA validation results from JSON log files.

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

            status = data.get("status", "").lower()
            judge_result = data.get("judge_result", "").upper()

            if status == "completed":
                results["completed_status"] += 1

                if judge_result == "CORRECT":
                    results["completed_and_correct"] += 1
                    completed_correct_files.append(json_file.name)
                else:
                    results["completed_and_incorrect"] += 1
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
    results: Dict[str, int],
    correct_files: List[str],
    incorrect_files: List[Tuple[str, str]],
    error_files: List[Tuple[str, str]],
) -> None:
    """Display the analysis results in a formatted way."""

    print("\n" + "=" * 60)
    print("GAIA VALIDATION RESULTS SUMMARY")
    print("=" * 60)

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

    if completed > 0:
        accuracy = correct / completed * 100
        print(f"\nAccuracy rate (correct/completed): {accuracy:.1f}%")

    print("\n" + "-" * 60)
    print(
        f"ANSWER: Among files marked as status 'completed', {correct} have judge_result 'CORRECT'"
    )
    print("-" * 60)

    # Show some example files for verification
    if correct_files:
        print("\nFirst 5 correct files:")
        for i, filename in enumerate(correct_files[:5], 1):
            print(f"  {i}. {filename}")
        if len(correct_files) > 5:
            print(f"  ... and {len(correct_files) - 5} more")

    if incorrect_files:
        print("\nFirst 5 incorrect files (with judge results):")
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

    # Default to the attached folder path
    default_folder = (
        "/home/binwang/projects/miroflow-private/logs/gaia-validation/20250911_1155"
    )

    # Check if folder path was provided as command line argument
    if len(sys.argv) > 1:
        log_folder = sys.argv[1]
        print(f"Using provided folder path: {log_folder}")
    else:
        log_folder = default_folder
        print(f"No folder path provided, using default: {log_folder}")

    try:
        print(f"Analyzing GAIA validation results in: {log_folder}")
        results, correct_files, incorrect_files, error_files = analyze_gaia_results(
            log_folder
        )
        display_results(results, correct_files, incorrect_files, error_files)

    except Exception as e:
        print(f"Error: {e}")
        print(f"\nUsage: python {sys.argv[0]} [LOG_FOLDER_PATH]")
        print(
            f"Example: python {sys.argv[0]} /path/to/logs/gaia-validation/20250911_2307"
        )
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
