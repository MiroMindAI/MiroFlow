#!/usr/bin/env python3
"""
GAIA Dataset Task Report Generator

This script generates detailed text reports for specified tasks in the GAIA-val dataset.
"""

import json
import os
import sys
from datetime import datetime


def find_gaia_data_dir():
    """Find GAIA data directory automatically"""
    # Get the directory where this script is located (utils/progress_check/)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Project root is two levels up from utils/progress_check/
    repo_root = os.path.abspath(os.path.join(script_dir, "..", ".."))
    
    # Try common locations
    possible_paths = [
        os.path.join(repo_root, "data", "gaia-val"),  # Project root/data/gaia-val
        os.path.join(script_dir, "..", "data", "gaia-val"),  # utils/data/gaia-val (unlikely)
        os.path.join(script_dir, "data", "gaia-val"),  # utils/progress_check/data/gaia-val (unlikely)
        "data/gaia-val",  # Relative from current working directory
    ]

    for path in possible_paths:
        abs_path = os.path.abspath(path)
        jsonl_path = os.path.join(abs_path, "standardized_data.jsonl")
        if os.path.exists(jsonl_path):
            return abs_path

    # If not found, return default path (project root/data/gaia-val)
    return os.path.join(repo_root, "data", "gaia-val")


def load_gaia_data(data_dir=None):
    """Load GAIA validation dataset"""
    if data_dir is None:
        data_dir = find_gaia_data_dir()

    jsonl_path = os.path.join(data_dir, "standardized_data.jsonl")

    if not os.path.exists(jsonl_path):
        print(f"❌ Error: GAIA data file not found at {jsonl_path}")
        print("Please ensure the GAIA dataset is available in one of these locations:")
        print("- data/gaia-val/standardized_data.jsonl")
        print("- ../data/gaia-val/standardized_data.jsonl")
        print("- Or specify the correct path using --data-dir argument")
        sys.exit(1)

    tasks = []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                tasks.append(json.loads(line))

    return tasks


def _default_reports_dir() -> str:
    """Return absolute path to the default GAIA reports directory."""
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    reports_dir = os.path.join(repo_root, "gaia_reports")
    return reports_dir


def generate_task_report(task_index, data_dir=None, output_dir=None):
    """Generate detailed text report for specified task"""
    print(f"🚀 Loading GAIA dataset...")
    tasks = load_gaia_data(data_dir)

    display_index = task_index + 1

    if task_index >= len(tasks):
        print(f"❌ Error: Task index {display_index} out of range, dataset has {len(tasks)} tasks")
        return None

    print(f"📄 Generating task {display_index} report...")

    # Get task data
    task = tasks[task_index]

    # Set output directory (default to <repo_root>/gaia_reports)
    if output_dir is None:
        output_dir = _default_reports_dir()

    # Ensure the directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Generate report file
    report_path = os.path.join(output_dir, f'gaia_task_{display_index}_report.txt')

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("=" * 80 + "\n")
        f.write(f"GAIA Dataset Task {display_index} Detailed Report\n")
        f.write("=" * 80 + "\n\n")

        # Basic information
        f.write("1. Task Basic Information\n")
        f.write("-" * 40 + "\n")
        f.write(f"Task ID: {task['task_id']}\n")
        f.write(f"Difficulty Level: Level {task['metadata']['Level']}\n")
        f.write(f"File Attachment: {'Yes' if task.get('file_path') else 'No'}\n")
        if task.get('file_path'):
            f.write(f"File Path: {task['file_path']}\n")
        f.write("\n")

        # Question content
        f.write("2. Question Content\n")
        f.write("-" * 40 + "\n")
        f.write(f"{task['task_question']}\n\n")

        # Ground truth answer
        f.write("3. Ground Truth Answer\n")
        f.write("-" * 40 + "\n")
        f.write(f"{task['ground_truth']}\n\n")

        # Solution steps
        f.write("4. Detailed Solution Steps\n")
        f.write("-" * 40 + "\n")
        f.write(f"{task['metadata']['Annotator Metadata']['Steps']}\n\n")

        # Metadata
        f.write("5. Task Metadata\n")
        f.write("-" * 40 + "\n")
        metadata = task['metadata']['Annotator Metadata']
        for key, value in metadata.items():
            if key != 'Steps':  # Skip Steps since it's shown in section 4
                if key == 'Tools':
                    f.write(f"{key}:\n{value}\n\n")
                else:
                    f.write(f"{key}: {value}\n\n")
        f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("End of Report\n")
        f.write("=" * 80 + "\n")

    print(f"📄 Task {display_index} detailed report saved to: {report_path}")

    return report_path


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description='Generate GAIA dataset task reports')
    parser.add_argument('task_index', nargs='?', type=int, default=1,
                       help='Task index to generate report for (1-based, default: 1)')
    parser.add_argument('--data-dir', type=str, default=None,
                       help='Path to GAIA data directory (auto-detected if not specified)')
    parser.add_argument('--output-dir', type=str, default=None,
                       help='Output directory for reports (default: <repo_root>/gaia_reports)')

    args = parser.parse_args()

    task_index = args.task_index - 1  # Convert to 0-based for internal use

    generate_task_report(task_index, args.data_dir, args.output_dir)


if __name__ == "__main__":
    main()

