#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# Configuration parameters - dual model configuration
NUM_RUNS=3
MAX_CONCURRENT=20
BENCHMARK_NAME="gaia-validation"
AGENT_SET="claude03_claude_dual"
ADD_MESSAGE_ID="true"  # Set to true to add random message ID to all messages sent to LLM
MAX_TURNS=-1

# Automatically set Chinese context - if BENCHMARK_NAME contains xbench or -zh
if [[ $BENCHMARK_NAME == "xbench-ds" ]] || [[ $BENCHMARK_NAME == "browsecomp-zh" ]]; then
    export CHINESE_CONTEXT="true"
    echo "检测到中文相关基准测试，已启用中文上下文：CHINESE_CONTEXT=true"
fi

# export REMOVE_SNIPPETS="true"
# export REMOVE_KNOWLEDGE_GRAPH="true"
export REMOVE_ANSWER_BOX="true"

export LOGGER_LEVEL="INFO"

RESULTS_DIR="logs/${BENCHMARK_NAME}/noansbox_${AGENT_SET}"

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
            agent=$AGENT_SET \
            agent.add_message_id=$ADD_MESSAGE_ID \
            agent.main_agent.max_turns=$MAX_TURNS \
            agent.sub_agents.agent-worker.max_turns=$MAX_TURNS \
            benchmark.execution.max_tasks=null \
            benchmark.execution.max_concurrent=$MAX_CONCURRENT \
            benchmark.execution.pass_at_k=1 \
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