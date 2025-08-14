#!/usr/bin/env python3

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import glob
import json
import os
import sys


def extract_score_from_log(run_dir, task_score_dict):
    # Traverse all task_{task_id}_attempt_*.log files to extract score
    log_files = glob.glob(os.path.join(run_dir, "*attempt*"))
    for log_file in log_files:
        task_id = log_file.split("/")[-1].split("_")[0]
        with open(log_file, "r") as f:
            data = json.load(f)
            if "llm_as_judge_result" in data and data["llm_as_judge_result"] in (
                "CORRECT",
                "INCORRECT",
            ):
                if task_id not in task_score_dict:
                    task_score_dict[task_id] = []
                task_score_dict[task_id].append(
                    data["llm_as_judge_result"] == "CORRECT"
                )


def calculate_majority_vote(task_score_dict):
    """Calculate majority vote results for each task."""
    majority_success_id = []
    majority_failed_id = []

    for task, scores in task_score_dict.items():
        if len(scores) == 0:
            continue
        correct_count = sum(scores)
        total_count = len(scores)

        # Majority vote: more than half of attempts are correct
        if correct_count > total_count / 2:
            majority_success_id.append(task)
        else:
            majority_failed_id.append(task)

    return majority_success_id, majority_failed_id


def main(results_dir: str, pass_at_k: int = 3):
    if not os.path.exists(results_dir):
        print(f"Results directory does not exist: {results_dir}")
        sys.exit(1)

    print(f"Analyzing results from: {results_dir}")

    # Traverse all run_* directories under results_dir
    run_dirs = glob.glob(os.path.join(results_dir, "run_*"))
    run_dirs = [i for i in run_dirs if os.path.isdir(i)]
    task_score_dict = {}
    for run_dir in run_dirs:
        if os.path.isdir(run_dir):
            extract_score_from_log(run_dir, task_score_dict)

    # Calculate Pass@k results
    success_id = []
    failed_id = []
    for task, scores in task_score_dict.items():
        if any(scores[:pass_at_k]):
            success_id.append(task)
        else:
            failed_id.append(task)

    # Calculate majority vote results
    majority_success_id, majority_failed_id = calculate_majority_vote(task_score_dict)

    # Save simple statistical results
    output_file = os.path.join(results_dir, f"average_scores_pass_at_{pass_at_k}.txt")
    with open(output_file, "w") as f:
        f.write("EVALUATION RESULTS\n")
        print("EVALUATION RESULTS\n")
        f.write("=" * 50 + "\n")
        print("=" * 50)
        f.write(f"Pass@{pass_at_k} Results:\n")
        print(f"Pass@{pass_at_k} Results:")
        f.write(f"Number of tasks: {len(task_score_dict)}\n")
        print(f"Number of tasks: {len(task_score_dict)}")
        f.write(f"Success @ {pass_at_k}: {len(success_id)}\n")
        print(f"Success @ {pass_at_k}: {len(success_id)}")
        f.write(f"Failed: {len(failed_id)}\n")
        print(f"Failed: {len(failed_id)}")
        f.write(
            f"Success rate @ {pass_at_k}: {len(success_id) / (len(success_id) + len(failed_id)) * 100:.2f}%\n"
        )
        print(
            f"Success rate @ {pass_at_k}: {len(success_id) / (len(success_id) + len(failed_id)) * 100:.2f}%\n"
        )
        f.write("=" * 50 + "\n")
        f.write("=" * 50 + "\n")

        f.write(f"Success id:\n{'\n'.join(success_id)}\n")
        f.write(f"Failed id:\n{'\n'.join(failed_id)}\n")

    print(f"\nResults saved to: {output_file}")

    # Save majority vote results
    print(f"Number of runs: {run_dirs}")
    majority_output_file = os.path.join(
        results_dir, f"majority_vote_at_{len(run_dirs)}.txt"
    )
    with open(majority_output_file, "w") as f:
        f.write("EVALUATION RESULTS\n")
        print("MAJORITY VOTE RESULTS\n")
        f.write("=" * 50 + "\n")
        print("=" * 50)
        f.write("Majority Vote Results:\n")
        print("Majority Vote Results:")
        f.write(f"Number of tasks: {len(task_score_dict)}\n")
        print(f"Number of tasks: {len(task_score_dict)}")
        f.write(f"Success (majority vote): {len(majority_success_id)}\n")
        print(f"Success (majority vote): {len(majority_success_id)}")
        f.write(f"Failed (majority vote): {len(majority_failed_id)}\n")
        print(f"Failed (majority vote): {len(majority_failed_id)}")
        total_tasks = len(majority_success_id) + len(majority_failed_id)
        if total_tasks > 0:
            majority_rate = len(majority_success_id) / total_tasks * 100
            f.write(f"Success rate (majority vote): {majority_rate:.2f}%\n")
            print(f"Success rate (majority vote): {majority_rate:.2f}%\n")
        f.write("=" * 50 + "\n")
        f.write("=" * 50 + "\n")

        f.write(f"Success id:\n{'\n'.join(majority_success_id)}\n")
        f.write(f"Failed id:\n{'\n'.join(majority_failed_id)}\n")

    print(f"Majority vote results saved to: {majority_output_file}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python calculate_score_from_log.py <results_dir> [pass_at_k]")
        sys.exit(1)

    results_dir = sys.argv[1]
    pass_at_k = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    main(results_dir, pass_at_k)
