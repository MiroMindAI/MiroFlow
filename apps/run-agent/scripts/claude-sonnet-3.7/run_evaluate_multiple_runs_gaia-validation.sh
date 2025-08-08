#!/bin/bash

# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# 配置参数
NUM_RUNS=3
BENCHMARK_NAME="gaia-validation"
LLM_PROVIDER="claude_openrouter"
# LLM_MODEL="anthropic/claude-sonnet-4"
LLM_MODEL="anthropic/claude-3.7-sonnet"
AGENT_SET="owl_set"

# 设置结果目录
RESULTS_DIR="logs/${BENCHMARK_NAME}/0726_${LLM_PROVIDER}_${LLM_MODEL}_${AGENT_SET}"

echo "Starting $NUM_RUNS runs of the evaluation..."
echo "Results will be saved in: $RESULTS_DIR"

# 创建结果目录
mkdir -p "$RESULTS_DIR"

# 启动所有并行任务
for i in $(seq 1 $NUM_RUNS); do
    echo "=========================================="
    echo "Launching experiment $i/$NUM_RUNS"
    echo "=========================================="
    
    # 设置这次运行的特定标识
    RUN_ID="run_$i"
    
    # 运行实验（后台运行）
    (
        uv run python benchmarks/common_benchmark.py \
            benchmark=$BENCHMARK_NAME \
            llm=claude_openrouter \
            llm.provider=$LLM_PROVIDER \
            llm.model_name=$LLM_MODEL \
            llm.async_client=true \
            benchmark.execution.max_tasks=null \
            benchmark.execution.max_concurrent=5 \
            benchmark.execution.pass_at_k=1 \
            agent=$AGENT_SET \
            hydra.run.dir=${RESULTS_DIR}/$RUN_ID \
            > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1
        
        # 检查运行是否成功
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
    
    # 稍微延迟启动，避免同时请求
    sleep 2
done

echo "All $NUM_RUNS runs have been launched in parallel"
echo "Waiting for all runs to complete..."

# 等待所有后台任务完成
wait

echo "=========================================="
echo "All $NUM_RUNS runs completed!"
echo "=========================================="

# 计算平均分数
echo "Calculating average scores..."
uv run python benchmarks/evaluators/calculate_average_score.py "$RESULTS_DIR"

echo "=========================================="
echo "Multiple runs evaluation completed!"
echo "Check results in: $RESULTS_DIR"
echo "Check individual run logs: $RESULTS_DIR/run_*_output.log"
echo "==========================================" 