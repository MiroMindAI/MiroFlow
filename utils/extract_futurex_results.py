#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FutureX Results Extractor and Aggregator

This script extracts predictions from MiroFlow benchmark results and can aggregate
multiple runs using majority voting to create FutureX submission files.

Features:
1. Extract predictions from single benchmark results
2. Aggregate multiple runs with majority voting
3. Generate FutureX-compatible submission files
4. Support both single-run and multi-run scenarios

Usage:
    # Extract from single run
    python extract_futurex_results.py logs/futurex-online-test

    # Aggregate multiple runs (if run_* subdirectories exist)
    python extract_futurex_results.py logs/futurex-online-multi-runs

    # Specify output file
    python extract_futurex_results.py logs/futurex-online-test -o my_submission.jsonl
"""

import argparse
import json
import os
from collections import Counter, defaultdict
from typing import Dict, List, Tuple


def majority_vote(
    preds: List[str], first_seen_order: Dict[str, int]
) -> Tuple[str, Dict[str, int]]:
    """
    Compute the majority-vote prediction for a list of candidate predictions.

    Tie-breaking rules (deterministic):
      1) Highest frequency wins.
      2) If there is a tie on frequency, choose the candidate that appeared earliest
         across all runs (based on the provided first_seen_order index).
      3) As a final guard (shouldn't be needed if first_seen_order is complete),
         fall back to lexicographic order.

    Returns:
      (chosen_prediction, counts_dict)
    """
    counter = Counter(preds)
    # Get the max vote count
    max_count = max(counter.values())
    # All candidates that share the max vote count
    tied = [c for c, cnt in counter.items() if cnt == max_count]

    if len(tied) == 1:
        chosen = tied[0]
    else:
        # Prefer the one seen earliest globally
        tied.sort(key=lambda x: (first_seen_order.get(x, float("inf")), x))
        chosen = tied[0]

    # Expose counts for optional debugging/inspection
    return chosen, dict(counter)


def discover_runs(results_dir: str) -> List[str]:
    """
    Discover subdirectories inside results_dir that potentially contain a
    'benchmark_results.jsonl'. We don't strictly require the subdir name to
    start with 'run_', but we sort the list to keep processing deterministic.
    """
    runs = []
    for name in sorted(os.listdir(results_dir)):
        path = os.path.join(results_dir, name)
        if os.path.isdir(path):
            fpath = os.path.join(path, "benchmark_results.jsonl")
            if os.path.isfile(fpath):
                runs.append(path)
    return runs


def extract_predictions_from_file(file_path: str) -> Dict[str, str]:
    """
    Extract predictions from a single benchmark_results.jsonl file.

    Args:
        file_path: Path to benchmark_results.jsonl file

    Returns:
        Dictionary mapping task_id to prediction
    """
    predictions = {}

    with open(file_path, "r", encoding="utf-8") as fin:
        for line_num, line in enumerate(fin, 1):
            line = line.strip()
            if not line:
                continue

            try:
                rec = json.loads(line)
            except json.JSONDecodeError as e:
                print(
                    f"Warning: Skipping malformed JSON at line {line_num} in {file_path}: {e}"
                )
                continue

            task_id = rec.get("task_id")
            pred = rec.get("model_boxed_answer")

            # Only accept non-empty strings; coerce to str for safety
            if task_id and pred is not None and str(pred).strip():
                pred_str = str(pred).strip()
                predictions[task_id] = pred_str

    return predictions


def aggregate_multiple_runs(
    results_dir: str,
) -> Tuple[Dict[str, List[str]], Dict[str, int]]:
    """
    Aggregate predictions from multiple runs in subdirectories.

    Args:
        results_dir: Directory containing run_* subdirectories

    Returns:
        Tuple of (predictions_by_task, first_seen_order)
    """
    # Maps task_id -> list of predictions collected across runs
    preds_by_task: Dict[str, List[str]] = defaultdict(list)

    # Track first-seen order index for each distinct prediction string across all runs.
    # This enables deterministic tie-breaking.
    first_seen_order: Dict[str, int] = {}
    next_order_idx = 0

    runs = discover_runs(results_dir)
    if not runs:
        raise FileNotFoundError(
            f"No run directories with 'benchmark_results.jsonl' found under: {results_dir}"
        )

    total_lines = 0
    used_lines = 0

    # Read and aggregate predictions
    for run_dir in runs:
        fpath = os.path.join(run_dir, "benchmark_results.jsonl")
        print(f"Reading: {fpath}")

        with open(fpath, "r", encoding="utf-8") as fin:
            for line in fin:
                total_lines += 1
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    # Skip malformed JSON lines, but keep going
                    continue

                task_id = rec.get("task_id")
                pred = rec.get("model_boxed_answer")

                # Only accept non-empty strings; coerce to str for safety
                if task_id and pred is not None and str(pred).strip():
                    pred_str = str(pred).strip()
                    preds_by_task[task_id].append(pred_str)
                    if pred_str not in first_seen_order:
                        first_seen_order[pred_str] = next_order_idx
                        next_order_idx += 1
                    used_lines += 1

    print(f"Collected from {len(runs)} run(s).")
    print(f"Read {total_lines} line(s), accepted {used_lines} record(s).")

    return preds_by_task, first_seen_order


def process_single_run(results_dir: str) -> Dict[str, str]:
    """
    Process a single run (direct benchmark_results.jsonl file).

    Args:
        results_dir: Directory containing benchmark_results.jsonl

    Returns:
        Dictionary mapping task_id to prediction
    """
    file_path = os.path.join(results_dir, "benchmark_results.jsonl")

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"benchmark_results.jsonl not found in: {results_dir}")

    print(f"Reading single run: {file_path}")
    predictions = extract_predictions_from_file(file_path)
    print(f"Extracted {len(predictions)} predictions from single run.")

    return predictions


def write_submission_file(
    predictions: Dict[str, str],
    output_file: str,
    is_aggregated: bool = False,
    vote_counts: Dict[str, Dict[str, int]] = None,
) -> None:
    """
    Write predictions to FutureX submission format.

    Args:
        predictions: Dictionary mapping task_id to prediction
        output_file: Output file path
        is_aggregated: Whether this is from aggregated runs
        vote_counts: Vote counts for each task (only for aggregated runs)
    """
    num_tasks = 0
    with open(output_file, "w", encoding="utf-8") as out:
        for task_id in sorted(predictions.keys()):
            prediction = predictions[task_id]

            # Create submission record
            record = {"id": task_id, "prediction": prediction}

            # Add vote information for aggregated runs
            if is_aggregated and vote_counts and task_id in vote_counts:
                record["vote_counts"] = vote_counts[task_id]

            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            num_tasks += 1

    print(f"✅ Submission saved to {output_file}")
    if is_aggregated:
        print(f"Aggregated {num_tasks} unique task_id(s) from multiple runs.")
    else:
        print(f"Extracted {num_tasks} predictions from single run.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract predictions from MiroFlow benchmark results and create FutureX submission files. "
        "Supports both single runs and multi-run aggregation with majority voting."
    )
    parser.add_argument(
        "results_dir",
        help="Path to results dir containing benchmark_results.jsonl or run_*/benchmark_results.jsonl",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output JSONL file path (default: <results_dir>/futurex_submission.jsonl)",
    )
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Force aggregation mode (look for run_* subdirectories)",
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Force single run mode (look for direct benchmark_results.jsonl)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    results_dir = os.path.abspath(args.results_dir)
    if not os.path.isdir(results_dir):
        raise FileNotFoundError(f"Results dir not found: {results_dir}")

    output_file = (
        os.path.abspath(args.output)
        if args.output
        else os.path.join(results_dir, "futurex_submission.jsonl")
    )

    # Determine processing mode
    runs = discover_runs(results_dir)
    single_file = os.path.join(results_dir, "benchmark_results.jsonl")

    if args.aggregate:
        if not runs:
            raise FileNotFoundError(
                f"No run directories found for aggregation in: {results_dir}"
            )
        mode = "aggregate"
    elif args.single:
        if not os.path.isfile(single_file):
            raise FileNotFoundError(
                f"benchmark_results.jsonl not found for single run in: {results_dir}"
            )
        mode = "single"
    else:
        # Auto-detect mode
        if runs and os.path.isfile(single_file):
            print("Both single run and multiple runs detected. Using aggregation mode.")
            print("Use --single to force single run mode.")
            mode = "aggregate"
        elif runs:
            mode = "aggregate"
        elif os.path.isfile(single_file):
            mode = "single"
        else:
            raise FileNotFoundError(
                f"No benchmark_results.jsonl files found in: {results_dir}"
            )

    print(f"Processing mode: {mode}")

    if mode == "aggregate":
        # Multi-run aggregation with majority voting
        preds_by_task, first_seen_order = aggregate_multiple_runs(results_dir)

        # Apply majority voting
        final_predictions = {}
        vote_counts = {}

        for task_id in preds_by_task:
            voted_pred, counts = majority_vote(preds_by_task[task_id], first_seen_order)
            final_predictions[task_id] = voted_pred
            vote_counts[task_id] = counts

        write_submission_file(
            final_predictions, output_file, is_aggregated=True, vote_counts=vote_counts
        )

    else:
        # Single run extraction
        predictions = process_single_run(results_dir)
        write_submission_file(predictions, output_file, is_aggregated=False)


if __name__ == "__main__":
    main()
