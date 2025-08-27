# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import json
from pathlib import Path


def analyze_json_files(folder_path):
    """
    Analyze judge_result and task_file_name statistics in JSON files
    """
    folder = Path(folder_path)

    # Initialize counters
    total_correct = 0
    total_incorrect = 0
    null_task_file_correct = 0
    null_task_file_incorrect = 0

    # Store processed file information
    processed_files = 0
    error_files = []

    print(f"Starting to analyze folder: {folder_path}")
    print("=" * 60)

    # Iterate through all JSON files in the folder
    for json_file in folder.glob("*.json"):
        try:
            processed_files += 1
            print(f"Processing file {processed_files}: {json_file.name}")

            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Count judge_result
            if "judge_result" in data:
                if data["judge_result"] == "CORRECT":
                    total_correct += 1
                elif data["judge_result"] == "INCORRECT":
                    total_incorrect += 1

                # Check if task_file_name under input is null
                if "input" in data and isinstance(data["input"], dict):
                    if data["input"].get("task_file_name") is None:
                        if data["judge_result"] == "CORRECT":
                            null_task_file_correct += 1
                        elif data["judge_result"] == "INCORRECT":
                            null_task_file_incorrect += 1

        except json.JSONDecodeError as e:
            error_files.append(f"{json_file.name}: JSON parsing error - {e}")
        except Exception as e:
            error_files.append(f"{json_file.name}: Other error - {e}")

    # Output statistics results
    print("\n" + "=" * 60)
    print("Statistics Results:")
    print("=" * 60)
    print(f"Total files processed: {processed_files}")
    print(f"Total CORRECT count: {total_correct}")
    print(f"Total INCORRECT count: {total_incorrect}")
    print(f"Total: {total_correct + total_incorrect}")
    print()
    print(f"CORRECT count when task_file_name is null: {null_task_file_correct}")
    print(f"INCORRECT count when task_file_name is null: {null_task_file_incorrect}")
    print(
        f"Total when task_file_name is null: {null_task_file_correct + null_task_file_incorrect}"
    )

    # Calculate percentages
    if total_correct + total_incorrect > 0:
        correct_percentage = (total_correct / (total_correct + total_incorrect)) * 100
        print(f"\nOverall accuracy: {correct_percentage:.2f}%")

    if null_task_file_correct + null_task_file_incorrect > 0:
        null_correct_percentage = (
            null_task_file_correct / (null_task_file_correct + null_task_file_incorrect)
        ) * 100
        print(f"Accuracy when task_file_name is null: {null_correct_percentage:.2f}%")

    # Output error file information
    if error_files:
        print("\n" + "=" * 60)
        print("Files with processing errors:")
        print("=" * 60)
        for error in error_files:
            print(f"  {error}")


if __name__ == "__main__":
    # Target folder path
    folder_path = ["<your_results_dirs>"]

    analyze_json_files(folder_path)
