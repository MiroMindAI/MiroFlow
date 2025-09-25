#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Multiple runs FinSearchComp evaluation script
# Based on the working command: uv run main.py common-benchmark --config_file_name=agent_finsearchcomp benchmark=finsearchcomp output_dir=logs/finsearchcomp/$(date +"%Y%m%d_%H%M")

# Configuration parameters
NUM_RUNS=${NUM_RUNS:-3}
MAX_TASKS=${MAX_TASKS:-1}
MAX_CONCURRENT=${MAX_CONCURRENT:-5}
BENCHMARK_NAME="finsearchcomp"
AGENT_SET=${AGENT_SET:-"agent_finsearchcomp"}

# Set results directory with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M)
RESULTS_DIR="logs/${BENCHMARK_NAME}/${AGENT_SET}_${TIMESTAMP}"

export LOGGER_LEVEL="INFO"

echo "🚀 Starting $NUM_RUNS runs of FinSearchComp evaluation..."
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

# Show progress summary
echo "=========================================="
echo "📊 Progress Summary:"
echo "=========================================="

echo "=========================================="
echo "🎯 Multiple runs FinSearchComp evaluation completed!"
echo "📁 Check results in: $RESULTS_DIR"
echo "📝 Check individual run logs: $RESULTS_DIR/run_*_output.log"
echo "=========================================="
echo ""
echo "💡 Usage examples:"
echo "   # Default: 3 runs with full dataset"
echo "   ./scripts/run_evaluate_multiple_runs_finsearchcomp.sh"
echo ""
echo "   # Custom parameters"
echo "   NUM_RUNS=5 MAX_TASKS=10 MAX_CONCURRENT=3 ./scripts/run_evaluate_multiple_runs_finsearchcomp.sh"
echo ""
echo "   # Different agent configuration"
echo "   AGENT_SET=agent_gaia-validation ./scripts/run_evaluate_multiple_runs_finsearchcomp.sh"
echo ""
echo "   # Limited tasks for testing"
echo "   MAX_TASKS=5 ./scripts/run_evaluate_multiple_runs_finsearchcomp.sh"
