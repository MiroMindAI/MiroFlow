#!/usr/bin/env python3
"""
Task-level comparison between Sogou+Google search experiment and Google-only baseline
for the browsecomp-zh benchmark.

Compares judge_result (CORRECT/INCORRECT) per task_id across runs.
For tasks with retries, uses the highest retry_id (the final result).
"""

import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SOGOU_DIR = Path(
    "/mnt/agent-framework/bin_wang/miroflow-private-2026/logs/browsecomp-zh/standard_browsecomp-zh_mirothinker_sogou_20260212_1035"
)
BASELINE_DIR = Path(
    "/mnt/agent-framework/bin_wang/miroflow-private-2026/logs/browsecomp-zh/standard_browsecomp-zh_mirothinker_20260211_2306"
)

RUNS = ["run_1", "run_2", "run_3"]

FILE_PATTERN = re.compile(r"task_(\d+)_attempt_(\d+)_retry_(\d+)\.json")


def parse_task_meta_fast(filepath):
    """Read first 8KB of a task JSON file and extract task_meta fields."""
    try:
        with open(filepath, "rb") as f:
            chunk = f.read(8192)
        text = chunk.decode("utf-8", errors="ignore")

        # We need to extract task_id, judge_result, and status from the partial JSON.
        # Since task_meta is near the top, we can use regex extraction for robustness.
        task_id_match = re.search(r'"task_id"\s*:\s*"(\d+)"', text)
        judge_match = re.search(r'"judge_result"\s*:\s*"([^"]*)"', text)
        status_match = re.search(r'"status"\s*:\s*"([^"]*)"', text)

        if not task_id_match:
            return None

        return {
            "task_id": task_id_match.group(1),
            "judge_result": judge_match.group(1) if judge_match else None,
            "status": status_match.group(1) if status_match else None,
        }
    except Exception as e:
        print(f"  WARNING: Could not parse {filepath}: {e}", file=sys.stderr)
        return None


def load_run_results(experiment_dir, run_name):
    """
    Load all task results for a given run directory.
    For tasks with multiple retries, keep only the highest retry_id.
    Returns dict: task_id -> {task_id, judge_result, status}
    """
    run_dir = experiment_dir / run_name
    if not run_dir.exists():
        print(f"  WARNING: {run_dir} does not exist", file=sys.stderr)
        return {}

    # First pass: find highest retry per task
    task_files = {}  # task_num -> (max_retry_id, filepath)
    for fname in os.listdir(run_dir):
        m = FILE_PATTERN.match(fname)
        if not m:
            continue
        task_num = int(m.group(1))
        retry_id = int(m.group(3))
        if task_num not in task_files or retry_id > task_files[task_num][0]:
            task_files[task_num] = (retry_id, run_dir / fname)

    # Second pass: parse task_meta from the selected files
    results = {}
    for task_num, (retry_id, filepath) in task_files.items():
        meta = parse_task_meta_fast(filepath)
        if meta and meta["task_id"] is not None:
            results[meta["task_id"]] = meta
        else:
            print(f"  WARNING: No task_meta found in {filepath}", file=sys.stderr)

    return results


def compare_run(sogou_results, baseline_results, run_name):
    """
    Compare sogou vs baseline for a single run.
    Returns dict with categorized task_ids.
    """
    # Union of all task_ids present in both
    all_task_ids = sorted(
        set(sogou_results.keys()) | set(baseline_results.keys()), key=lambda x: int(x)
    )

    both_correct = []
    both_wrong = []
    improvements = []  # sogou CORRECT, baseline INCORRECT
    regressions = []  # baseline CORRECT, sogou INCORRECT
    sogou_only = []  # task only in sogou
    baseline_only = []  # task only in baseline
    sogou_missing_judge = []
    baseline_missing_judge = []

    for tid in all_task_ids:
        s = sogou_results.get(tid)
        b = baseline_results.get(tid)

        if s is None:
            baseline_only.append(tid)
            continue
        if b is None:
            sogou_only.append(tid)
            continue

        s_correct = s.get("judge_result") == "CORRECT"
        b_correct = b.get("judge_result") == "CORRECT"

        # Handle missing judge results
        if s.get("judge_result") is None:
            sogou_missing_judge.append(tid)
        if b.get("judge_result") is None:
            baseline_missing_judge.append(tid)

        if s_correct and b_correct:
            both_correct.append(tid)
        elif s_correct and not b_correct:
            improvements.append(tid)
        elif not s_correct and b_correct:
            regressions.append(tid)
        else:
            both_wrong.append(tid)

    return {
        "both_correct": both_correct,
        "both_wrong": both_wrong,
        "improvements": improvements,
        "regressions": regressions,
        "sogou_only": sogou_only,
        "baseline_only": baseline_only,
        "sogou_missing_judge": sogou_missing_judge,
        "baseline_missing_judge": baseline_missing_judge,
        "total_common": len(all_task_ids) - len(sogou_only) - len(baseline_only),
        "sogou_correct": len(both_correct) + len(improvements),
        "baseline_correct": len(both_correct) + len(regressions),
    }


def print_run_comparison(comparison, run_name):
    """Print detailed comparison for a single run."""
    print(f"\n{'='*80}")
    print(f"  {run_name} COMPARISON")
    print(f"{'='*80}")

    total = comparison["total_common"]
    sogou_acc = comparison["sogou_correct"]
    base_acc = comparison["baseline_correct"]

    print(f"\n  Tasks in common: {total}")
    print(f"  Sogou+Google correct:  {sogou_acc}/{total} ({100*sogou_acc/total:.1f}%)")
    print(f"  Baseline correct:      {base_acc}/{total} ({100*base_acc/total:.1f}%)")
    print(f"  Delta:                 {sogou_acc - base_acc:+d} tasks")

    print(f"\n  Both CORRECT:   {len(comparison['both_correct'])} tasks")
    print(f"  Both WRONG:     {len(comparison['both_wrong'])} tasks")
    print(
        f"  IMPROVEMENTS (sogou CORRECT, baseline WRONG): {len(comparison['improvements'])} tasks"
    )
    print(
        f"  REGRESSIONS  (baseline CORRECT, sogou WRONG): {len(comparison['regressions'])} tasks"
    )

    if comparison["improvements"]:
        print(f"\n  IMPROVEMENT task_ids ({len(comparison['improvements'])}):")
        for tid in comparison["improvements"]:
            print(f"    task_{tid}")

    if comparison["regressions"]:
        print(f"\n  REGRESSION task_ids ({len(comparison['regressions'])}):")
        for tid in comparison["regressions"]:
            print(f"    task_{tid}")

    if comparison["sogou_only"]:
        print(
            f"\n  Tasks ONLY in Sogou ({len(comparison['sogou_only'])}): {comparison['sogou_only']}"
        )
    if comparison["baseline_only"]:
        print(
            f"\n  Tasks ONLY in Baseline ({len(comparison['baseline_only'])}): {comparison['baseline_only']}"
        )
    if comparison["sogou_missing_judge"]:
        print(
            f"\n  Sogou tasks with missing judge_result: {comparison['sogou_missing_judge']}"
        )
    if comparison["baseline_missing_judge"]:
        print(
            f"\n  Baseline tasks with missing judge_result: {comparison['baseline_missing_judge']}"
        )


def main():
    print("=" * 80)
    print("  BROWSECOMP-ZH: SOGOU+GOOGLE vs BASELINE (Google only)")
    print("  Task-Level Comparison Report")
    print("=" * 80)
    print(f"\n  Sogou+Google dir: {SOGOU_DIR}")
    print(f"  Baseline dir:     {BASELINE_DIR}")

    all_comparisons = {}
    all_improvements = defaultdict(int)  # task_id -> count of runs where improved
    all_regressions = defaultdict(int)  # task_id -> count of runs where regressed

    for run_name in RUNS:
        print(f"\n  Loading {run_name}...")
        sogou_results = load_run_results(SOGOU_DIR, run_name)
        baseline_results = load_run_results(BASELINE_DIR, run_name)
        print(f"    Sogou tasks:    {len(sogou_results)}")
        print(f"    Baseline tasks: {len(baseline_results)}")

        comparison = compare_run(sogou_results, baseline_results, run_name)
        all_comparisons[run_name] = comparison
        print_run_comparison(comparison, run_name)

        for tid in comparison["improvements"]:
            all_improvements[tid] += 1
        for tid in comparison["regressions"]:
            all_regressions[tid] += 1

    # =========================================================================
    # Cross-run consistency analysis
    # =========================================================================
    print(f"\n{'='*80}")
    print("  CROSS-RUN CONSISTENCY ANALYSIS")
    print(f"{'='*80}")

    # Improvements appearing in multiple runs
    print("\n  --- CONSISTENT IMPROVEMENTS (sogou better in multiple runs) ---")
    for count in [3, 2]:
        tasks = sorted(
            [tid for tid, c in all_improvements.items() if c == count], key=int
        )
        if tasks:
            print(f"\n  Improved in {count}/3 runs ({len(tasks)} tasks):")
            for tid in tasks:
                print(f"    task_{tid}")

    one_time_imp = sorted(
        [tid for tid, c in all_improvements.items() if c == 1], key=int
    )
    if one_time_imp:
        print(f"\n  Improved in only 1/3 runs ({len(one_time_imp)} tasks):")
        for tid in one_time_imp:
            # Show which run
            runs_with_improvement = [
                r for r in RUNS if tid in all_comparisons[r]["improvements"]
            ]
            print(f"    task_{tid}  ({', '.join(runs_with_improvement)})")

    # Regressions appearing in multiple runs
    print("\n  --- CONSISTENT REGRESSIONS (sogou worse in multiple runs) ---")
    for count in [3, 2]:
        tasks = sorted(
            [tid for tid, c in all_regressions.items() if c == count], key=int
        )
        if tasks:
            print(f"\n  Regressed in {count}/3 runs ({len(tasks)} tasks):")
            for tid in tasks:
                print(f"    task_{tid}")

    one_time_reg = sorted(
        [tid for tid, c in all_regressions.items() if c == 1], key=int
    )
    if one_time_reg:
        print(f"\n  Regressed in only 1/3 runs ({len(one_time_reg)} tasks):")
        for tid in one_time_reg:
            runs_with_regression = [
                r for r in RUNS if tid in all_comparisons[r]["regressions"]
            ]
            print(f"    task_{tid}  ({', '.join(runs_with_regression)})")

    # Mixed tasks: improved in some runs, regressed in others
    mixed_tasks = sorted(
        set(all_improvements.keys()) & set(all_regressions.keys()), key=int
    )
    if mixed_tasks:
        print("\n  --- MIXED TASKS (improved in some runs, regressed in others) ---")
        print(f"  {len(mixed_tasks)} tasks:")
        for tid in mixed_tasks:
            imp_runs = [r for r in RUNS if tid in all_comparisons[r]["improvements"]]
            reg_runs = [r for r in RUNS if tid in all_comparisons[r]["regressions"]]
            print(f"    task_{tid}: improved in {imp_runs}, regressed in {reg_runs}")

    # =========================================================================
    # Summary table across all runs
    # =========================================================================
    print(f"\n{'='*80}")
    print("  SUMMARY TABLE")
    print(f"{'='*80}")
    print(
        f"\n  {'Run':<8} {'Sogou Acc':>10} {'Base Acc':>10} {'Delta':>8} {'Improve':>9} {'Regress':>9} {'Both OK':>9} {'Both Bad':>9}"
    )
    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*8} {'-'*9} {'-'*9} {'-'*9} {'-'*9}")

    total_sogou = 0
    total_base = 0
    total_n = 0
    for run_name in RUNS:
        c = all_comparisons[run_name]
        n = c["total_common"]
        s = c["sogou_correct"]
        b = c["baseline_correct"]
        total_sogou += s
        total_base += b
        total_n += n
        print(
            f"  {run_name:<8} {s:>4}/{n:<4}  {b:>4}/{n:<4}  {s-b:>+5}    {len(c['improvements']):>5}     {len(c['regressions']):>5}     {len(c['both_correct']):>5}     {len(c['both_wrong']):>5}"
        )

    print(f"  {'-'*8} {'-'*10} {'-'*10} {'-'*8} {'-'*9} {'-'*9} {'-'*9} {'-'*9}")
    avg_s = total_sogou / 3
    avg_b = total_base / 3
    avg_n = total_n / 3
    print(
        f"  {'Avg':<8} {avg_s:>5.1f}/{avg_n:<5.0f} {avg_b:>5.1f}/{avg_n:<5.0f} {avg_s-avg_b:>+5.1f}"
    )

    # Unique improvements and regressions across all runs
    print(
        f"\n  Total unique tasks that improved in at least one run: {len(all_improvements)}"
    )
    print(
        f"  Total unique tasks that regressed in at least one run: {len(all_regressions)}"
    )
    print(
        f"  Tasks that consistently improved (3/3 runs):  {len([t for t,c in all_improvements.items() if c==3])}"
    )
    print(
        f"  Tasks that consistently regressed (3/3 runs): {len([t for t,c in all_regressions.items() if c==3])}"
    )
    print(
        f"  Tasks that improved in >=2/3 runs: {len([t for t,c in all_improvements.items() if c>=2])}"
    )
    print(
        f"  Tasks that regressed in >=2/3 runs: {len([t for t,c in all_regressions.items() if c>=2])}"
    )

    print()


if __name__ == "__main__":
    main()
