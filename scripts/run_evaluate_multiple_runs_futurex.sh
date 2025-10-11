#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Multiple runs FutureX evaluation script
# Based on the working command: uv run main.py common-benchmark --config_file_name=agent_quickstart_reading benchmark=futurex output_dir=logs/futurex-test

# Configuration parameters
NUM_RUNS=${NUM_RUNS:-3}
MAX_TASKS=${MAX_TASKS:-null}
MAX_CONCURRENT=${MAX_CONCURRENT:-5}
BENCHMARK_NAME="futurex"
AGENT_SET=${AGENT_SET:-"agent_quickstart_reading"}

# TODO: Add more settings like message ID and max turns, currently not supported using agent_quickstart_reading
# ADD_MESSAGE_ID=${ADD_MESSAGE_ID:-"false"}
# MAX_TURNS=${MAX_TURNS:-1}

# Set results directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M)
RESULTS_DIR="logs/${BENCHMARK_NAME}/${AGENT_SET}_${TIMESTAMP}"

export LOGGER_LEVEL="INFO"

echo "🚀 Starting $NUM_RUNS runs of FutureX evaluation..."
echo "📊 Using max_tasks: $MAX_TASKS (set MAX_TASKS=null for full dataset)"
echo "📊 Using max_concurrent: $MAX_CONCURRENT"
echo "📁 Results will be saved in: $RESULTS_DIR"

# Create results directory
mkdir -p "$RESULTS_DIR"

# Launch all parallel tasks
for i in $(seq 1 $NUM_RUNS); do
    echo "=========================================="
    echo "🚀 Launching experiment $i/$NUM_RUNS"
    echo "📝 Output log: $RESULTS_DIR/run_${i}_output.log"
    echo "=========================================="
    
    # Set specific identifier for this run
    RUN_ID="run_$i"
    
    # Run experiment (background execution)
    (
        echo "Starting run $i at $(date)"
        uv run main.py common-benchmark \
            --config_file_name=$AGENT_SET \
            benchmark=$BENCHMARK_NAME \
            benchmark.execution.max_tasks=$MAX_TASKS \
            benchmark.execution.max_concurrent=$MAX_CONCURRENT \
            benchmark.execution.pass_at_k=1 \
            output_dir=${RESULTS_DIR}/$RUN_ID \
            hydra.run.dir=${RESULTS_DIR}/$RUN_ID \
            > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1
        
        # Check if run was successful
        if [ $? -eq 0 ]; then
            echo "✅ Run $i completed successfully at $(date)"
            RESULT_FILE=$(find "${RESULTS_DIR}/$RUN_ID" -name "*accuracy.txt" 2>/dev/null | head -1)
            if [ -f "$RESULT_FILE" ]; then
                echo "📊 Results saved to $RESULT_FILE"
            else
                echo "⚠️  Warning: Result file not found for run $i"
            fi
        else
            echo "❌ Run $i failed at $(date)!"
        fi
    ) &
    
    # Small delay between launches
    sleep 2
done

echo "🎯 All $NUM_RUNS runs have been launched in parallel"
echo "⏳ Waiting for all runs to complete..."

# Wait for all background tasks to complete
wait

echo "=========================================="
echo "🎉 All $NUM_RUNS runs completed!"
echo "=========================================="

# Extract predictions and format for FutureX submission
echo "📤 Extracting predictions and formatting for FutureX submission..."
uv run python utils/extract_futurex_results.py "$RESULTS_DIR"

# Check status and provide user-friendly message
if [ $? -eq 0 ]; then
    echo "✅ Submission file generated: $RESULTS_DIR/futurex_submission.jsonl"
    echo "📋 You can now upload this file to the FutureX test server."
else
    echo "❌ Failed to generate submission file. Please check the logs for details."
fi

# Show progress summary
echo "=========================================="
echo "📊 Progress Summary:"
echo "=========================================="

echo "=========================================="
echo "🎯 Multiple runs FutureX evaluation completed!"
echo "📁 Check results in: $RESULTS_DIR"
echo "📝 Check individual run logs: $RESULTS_DIR/run_*_output.log"
echo "📤 Check submission file: $RESULTS_DIR/futurex_submission.jsonl"
echo "=========================================="
echo ""
echo "💡 Usage examples:"
echo "   # Default: 3 runs with full dataset"
echo "   ./scripts/run_evaluate_multiple_runs_futurex.sh"
echo ""
echo "   # Custom parameters"
echo "   NUM_RUNS=5 MAX_TASKS=10 MAX_CONCURRENT=3 ./scripts/run_evaluate_multiple_runs_futurex.sh"
echo ""
echo "   # Different agent configuration"
echo "   AGENT_SET=agent_gaia-validation ./scripts/run_evaluate_multiple_runs_futurex.sh"
echo ""
echo "   # Limited tasks for testing"
echo "   MAX_TASKS=5 ./scripts/run_evaluate_multiple_runs_futurex.sh"