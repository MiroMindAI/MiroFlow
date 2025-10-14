#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Configuration parameters
NUM_RUNS=8
AGENT_SET="agent_gaia-validation-text-only_mirothinker_single_agent"
MAX_CONCURRENT=8

# Set results directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M)
RESULTS_DIR=${RESULTS_DIR:-"logs/${BENCHMARK_NAME}/${AGENT_SET}_${TIMESTAMP}"}

echo "Starting $NUM_RUNS runs of the evaluation..."
echo "Results will be saved in: $RESULTS_DIR"

# Create results directory
mkdir -p "$RESULTS_DIR"

for i in $(seq 1 $NUM_RUNS); do
    echo "=========================================="
    echo "Launching experiment $i/$NUM_RUNS"
    echo "=========================================="
    
    RUN_ID="run_$i"
    
    (
        uv run main.py common-benchmark \
            --config_file_name=$AGENT_SET \
            benchmark.execution.max_concurrent=$MAX_CONCURRENT \
            output_dir="$RESULTS_DIR/$RUN_ID" \
            hydra.run.dir=${RESULTS_DIR}/$RUN_ID \
            > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1
        
        if [ $? -eq 0 ]; then
            echo "Run $i completed successfully"
            RESULT_FILE=$(find "${RESULTS_DIR}/$RUN_ID" -name "*accuracy.txt" 2>/dev/null | head -1)
            if [ -f "$RESULT_FILE" ]; then
                echo "Results saved to $RESULT_FILE"
            else
                echo "Warning: Result file not found for run $i"
            fi
        else
            echo "Run $i failed!"
        fi
    ) &
    
    sleep 2
done

echo "All $NUM_RUNS runs have been launched in parallel"
echo "Waiting for all runs to complete..."

wait

echo "=========================================="
echo "All $NUM_RUNS runs completed!"
echo "=========================================="

echo "Calculating average scores..."
uv run main.py avg-score "$RESULTS_DIR"

echo "=========================================="
echo "Multiple runs evaluation completed!"
echo "Check results in: $RESULTS_DIR"
echo "Check individual run logs: $RESULTS_DIR/run_*_output.log"
echo "==========================================" 

