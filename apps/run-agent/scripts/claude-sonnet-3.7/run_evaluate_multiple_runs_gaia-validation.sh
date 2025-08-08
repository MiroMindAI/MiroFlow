#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

NUM_RUNS=3
BENCHMARK_NAME="gaia-validation"
LLM_PROVIDER="claude_openrouter"
LLM_MODEL="anthropic/claude-3.7-sonnet"
AGENT_SET="miroflow"

RESULTS_DIR="logs/${BENCHMARK_NAME}/${LLM_PROVIDER}_${LLM_MODEL}_${AGENT_SET}"

echo "Starting $NUM_RUNS runs of the evaluation..."
echo "Results will be saved in: $RESULTS_DIR"

mkdir -p "$RESULTS_DIR"

for i in $(seq 1 $NUM_RUNS); do
    echo "=========================================="
    echo "Launching experiment $i/$NUM_RUNS"
    echo "=========================================="
    
    RUN_ID="run_$i"
    
    (
        uv run main.py common-benchmark \
            benchmark=$BENCHMARK_NAME \
            llm=claude_openrouter \
            llm.provider=$LLM_PROVIDER \
            llm.model_name=$LLM_MODEL \
            llm.async_client=true \
            benchmark.execution.max_tasks=null \
            benchmark.execution.max_concurrent=5 \
            benchmark.execution.pass_at_k=1 \
            agent=$AGENT_SET \
            output_dir="$RESULTS_DIR/$RUN_ID" \
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