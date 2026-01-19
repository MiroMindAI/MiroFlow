#!/usr/bin/env python3
"""
Generic Benchmark Task Report Generator

This script generates detailed text reports for tasks from benchmark log files.
Works with any benchmark dataset (GAIA, FinSearchComp, FutureX, etc.)
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any


def find_task_log_file(log_dir: str, task_id: str, attempt: int = 1) -> Optional[Path]:
    """Find task log file in the log directory"""
    log_path = Path(log_dir)
    if not log_path.exists():
        return None
    
    # Try to find the log file
    pattern = f"task_{task_id}_attempt_{attempt}.json"
    log_file = log_path / pattern
    
    if log_file.exists():
        return log_file
    
    # Try without attempt number
    pattern = f"task_{task_id}.json"
    log_file = log_path / pattern
    if log_file.exists():
        return log_file
    
    return None


def load_task_from_log(log_file: Path) -> Optional[Dict[str, Any]]:
    """Load task data from log file"""
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return None


def extract_question(log_data: Dict[str, Any]) -> str:
    """Extract question from log data in various formats"""
    # Try different possible locations
    if "task_question" in log_data:
        return log_data["task_question"]
    
    if "input" in log_data:
        input_data = log_data["input"]
        if isinstance(input_data, dict):
            if "task_description" in input_data:
                return input_data["task_description"]
            elif "task_question" in input_data:
                return input_data["task_question"]
        elif isinstance(input_data, str):
            return input_data
    
    return "N/A"


def extract_metadata_info(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata information from log data"""
    metadata_info = {}
    
    # Try to get metadata from various locations
    metadata = log_data.get("metadata", {})
    if isinstance(metadata, dict):
        metadata_info.update(metadata)
    
    # Also check input.metadata
    if "input" in log_data and isinstance(log_data["input"], dict):
        input_metadata = log_data["input"].get("metadata", {})
        if isinstance(input_metadata, dict):
            metadata_info.update(input_metadata)
    
    return metadata_info


def generate_task_report_from_log(
    log_dir: str, 
    task_id: str, 
    attempt: int = 1,
    output_dir: Optional[str] = None
) -> Optional[str]:
    """Generate detailed text report from task log file"""
    
    # Find the log file
    log_file = find_task_log_file(log_dir, task_id, attempt)
    if not log_file:
        print(f"❌ Error: Log file not found for task {task_id} (attempt {attempt})")
        return None
    
    # Load task data
    log_data = load_task_from_log(log_file)
    if not log_data:
        print(f"❌ Error: Failed to load log file: {log_file}")
        return None
    
    # Set output directory (default to log_dir/reports)
    if output_dir is None:
        output_dir = os.path.join(log_dir, "reports")
    
    # Ensure the directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate report file
    report_filename = f"task_{task_id}_report.txt"
    report_path = os.path.join(output_dir, report_filename)
    
    # Extract information
    question = extract_question(log_data)
    ground_truth = log_data.get("ground_truth", "N/A")
    final_answer = log_data.get("final_boxed_answer", log_data.get("final_answer", "N/A"))
    status = log_data.get("status", "unknown")
    judge_result = log_data.get("judge_result", "N/A")
    error = log_data.get("error", "")
    
    # Extract execution time
    execution_time = None
    start_time = log_data.get("start_time")
    end_time = log_data.get("end_time")
    if start_time and end_time:
        try:
            from datetime import datetime
            start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            execution_time = (end_dt - start_dt).total_seconds()
        except Exception:
            pass
    
    # Extract metadata
    metadata_info = extract_metadata_info(log_data)
    
    # Generate report
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write(f"Benchmark Task Report: {task_id}\n")
        f.write("=" * 80 + "\n\n")
        
        # Basic information
        f.write("1. Task Basic Information\n")
        f.write("-" * 40 + "\n")
        f.write(f"Task ID: {task_id}\n")
        f.write(f"Status: {status}\n")
        f.write(f"Judge Result: {judge_result}\n")
        if execution_time:
            f.write(f"Execution Time: {execution_time:.2f} seconds\n")
        if log_data.get("task_file_name"):
            f.write(f"File Attachment: {log_data['task_file_name']}\n")
        f.write("\n\n")
        
        # Question content
        f.write("2. Question Content\n")
        f.write("-" * 40 + "\n")
        f.write(f"{question}\n\n\n")
        
        # Ground truth answer
        f.write("3. Ground Truth Answer\n")
        f.write("-" * 40 + "\n")
        f.write(f"{ground_truth}\n\n\n")
        
        # Model answer
        f.write("4. Model Answer\n")
        f.write("-" * 40 + "\n")
        f.write(f"{final_answer}\n\n\n")
        
        # Error information (if any)
        if error:
            f.write("5. Error Information\n")
            f.write("-" * 40 + "\n")
            f.write(f"{error}\n\n\n")
        
        # Metadata (if available)
        if metadata_info:
            f.write("6. Task Metadata\n")
            f.write("-" * 40 + "\n")
            for key, value in metadata_info.items():
                if isinstance(value, dict):
                    f.write(f"{key}:\n")
                    for sub_key, sub_value in value.items():
                        f.write(f"  {sub_key}: {sub_value}\n")
                elif isinstance(value, list):
                    f.write(f"{key}: {', '.join(map(str, value))}\n")
                else:
                    f.write(f"{key}: {value}\n")
            f.write("\n\n")
        
        # Execution steps (if available)
        if "step_logs" in log_data and log_data["step_logs"]:
            f.write("7. Execution Steps\n")
            f.write("-" * 40 + "\n")
            f.write(f"Total steps: {len(log_data['step_logs'])}\n")
            # Optionally include step details
            f.write("\n")
        
        f.write("=" * 80 + "\n")
        f.write("End of Report\n")
        f.write("=" * 80 + "\n")
    
    print(f"📄 Task {task_id} report saved to: {report_path}")
    return report_path


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate benchmark task reports from log files")
    parser.add_argument(
        "log_dir",
        type=str,
        help="Path to benchmark log directory",
    )
    parser.add_argument(
        "task_id",
        type=str,
        help="Task ID to generate report for",
    )
    parser.add_argument(
        "--attempt",
        type=int,
        default=1,
        help="Attempt number (default: 1)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="Output directory for reports (default: <log_dir>/reports)",
    )
    
    args = parser.parse_args()
    
    generate_task_report_from_log(
        args.log_dir,
        args.task_id,
        args.attempt,
        args.output_dir
    )


if __name__ == "__main__":
    main()

