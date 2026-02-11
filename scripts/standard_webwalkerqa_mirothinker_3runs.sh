#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Configuration parameters
NUM_RUNS=3
BENCHMARK_NAME="webwalkerqa"
AGENT_SET="standard_webwalkerqa_mirothinker"
MAX_CONCURRENT=80

# Set results directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M)
RESULTS_DIR=${RESULTS_DIR:-"logs/${BENCHMARK_NAME}/${AGENT_SET}_${TIMESTAMP}"}

# Unique identifier for this run (used for cleanup)
RUN_MARKER="$$_${AGENT_SET}"

cleanup() {
    echo ""
    echo "Received interrupt signal, terminating all processes..."

    # Kill all Python processes related to this benchmark run
    pkill -TERM -f "test_benchmark.py.*${AGENT_SET}" 2>/dev/null
    pkill -TERM -f "mcp_server.*${AGENT_SET}" 2>/dev/null

    # Wait a moment for graceful shutdown
    sleep 2

    # Force kill any remaining processes
    pkill -KILL -f "test_benchmark.py.*${AGENT_SET}" 2>/dev/null
    pkill -KILL -f "mcp_server" 2>/dev/null

    # Also kill any child processes of this script
    pkill -TERM -P $$ 2>/dev/null
    sleep 1
    pkill -KILL -P $$ 2>/dev/null

    echo "All processes terminated."
    exit 130
}

# Only cleanup on interrupt signals, not on normal exit
trap cleanup SIGINT SIGTERM

echo "Starting $NUM_RUNS runs of the evaluation..."
echo "Benchmark: $BENCHMARK_NAME (680 tasks)"
echo "Results will be saved in: $RESULTS_DIR"

# Create results directory
mkdir -p "$RESULTS_DIR"

for i in $(seq 1 $NUM_RUNS); do
    echo "=========================================="
    echo "Launching experiment $i/$NUM_RUNS"
    echo "=========================================="

    RUN_ID="run_$i"

    # Start process in background
    uv run src/benchmark/run_benchmark.py \
        --config-path config/${AGENT_SET}.yaml \
        benchmark.execution.max_concurrent=$MAX_CONCURRENT \
        output_dir="$RESULTS_DIR/$RUN_ID" \
        > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1 &

    sleep 2
done

echo "All $NUM_RUNS runs have been launched in parallel"
echo "Waiting for all runs to complete..."
echo "Press Ctrl+C to terminate all processes"

# Wait for all background jobs
wait

# Check results after completion
for i in $(seq 1 $NUM_RUNS); do
    RUN_ID="run_$i"
    RESULT_FILE=$(find "${RESULTS_DIR}/$RUN_ID" -name "*accuracy.txt" 2>/dev/null | head -1)
    if [ -f "$RESULT_FILE" ]; then
        echo "Run $i: $(cat "$RESULT_FILE")"
    else
        JSON_COUNT=$(find "${RESULTS_DIR}/$RUN_ID" -name "task_*.json" 2>/dev/null | wc -l)
        if [ "$JSON_COUNT" -gt 0 ]; then
            echo "Run $i: $JSON_COUNT task logs generated"
        else
            echo "Run $i: No results found"
        fi
    fi
done

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
