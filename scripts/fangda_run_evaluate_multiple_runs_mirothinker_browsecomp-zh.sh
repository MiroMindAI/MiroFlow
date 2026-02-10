#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Configuration parameters
NUM_RUNS=3
BENCHMARK_NAME="browsecomp-zh"
AGENT_SET="fangda_agent_browsecomp-zh_mirothinker"
MAX_CONCURRENT=50

# Set results directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M)
RESULTS_DIR=${RESULTS_DIR:-"logs/${BENCHMARK_NAME}/${AGENT_SET}_${TIMESTAMP}"}

# Array to track child PIDs
declare -a CHILD_PIDS=()

cleanup() {
    echo ""
    echo "Received interrupt signal, terminating all processes..."
    for pid in "${CHILD_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Killing process group $pid"
            kill -TERM -"$pid" 2>/dev/null
        fi
    done
    # Wait a moment for graceful shutdown
    sleep 2
    # Force kill any remaining processes
    for pid in "${CHILD_PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "Force killing process group $pid"
            kill -KILL -"$pid" 2>/dev/null
        fi
    done
    echo "All processes terminated."
    exit 130
}

trap cleanup SIGINT SIGTERM

echo "Starting $NUM_RUNS runs of the evaluation..."
echo "Results will be saved in: $RESULTS_DIR"

# Create results directory
mkdir -p "$RESULTS_DIR"

for i in $(seq 1 $NUM_RUNS); do
    echo "=========================================="
    echo "Launching experiment $i/$NUM_RUNS"
    echo "=========================================="
    
    RUN_ID="run_$i"
    
    # Start process in new process group (set -m creates new pgrp)
    (
        set -m
        uv run src/benchmark/run_benchmark.py \
            --config-path config/${AGENT_SET}.yaml \
            benchmark.execution.max_concurrent=$MAX_CONCURRENT \
            output_dir="$RESULTS_DIR/$RUN_ID" \
            > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1
        
        EXIT_CODE=$?
        if [ $EXIT_CODE -eq 0 ]; then
            echo "Run $i completed successfully"
            RESULT_FILE=$(find "${RESULTS_DIR}/$RUN_ID" -name "*accuracy.txt" 2>/dev/null | head -1)
            if [ -f "$RESULT_FILE" ]; then
                echo "Results saved to $RESULT_FILE"
            else
                echo "Warning: Result file not found for run $i"
            fi
        else
            # Check if we have JSON result files (task completed but evaluator had issues)
            JSON_COUNT=$(find "${RESULTS_DIR}/$RUN_ID" -name "task_*.json" 2>/dev/null | wc -l)
            if [ "$JSON_COUNT" -gt 0 ]; then
                echo "Run $i finished with exit code $EXIT_CODE but generated $JSON_COUNT task logs"
            else
                echo "Run $i failed with exit code $EXIT_CODE"
            fi
        fi
    ) &
    
    # Get the PID and store it
    CHILD_PIDS+=($!)
    
    sleep 2
done

echo "All $NUM_RUNS runs have been launched in parallel"
echo "Child PIDs: ${CHILD_PIDS[*]}"
echo "Waiting for all runs to complete..."
echo "Press Ctrl+C to terminate all processes"

wait

echo "=========================================="
echo "All $NUM_RUNS runs completed!"
echo "=========================================="

echo "Calculating average scores..."
uv run python -c "from src.benchmark.calculate_average_score import main; main('$RESULTS_DIR')"

echo "=========================================="
echo "Multiple runs evaluation completed!"
echo "Check results in: $RESULTS_DIR"
echo "Check individual run logs: $RESULTS_DIR/run_*_output.log"
echo "=========================================="
