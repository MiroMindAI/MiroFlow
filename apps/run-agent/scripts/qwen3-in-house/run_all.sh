# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

# 解析命令行参数
# 用法: bash run_all.sh [LLM_MODEL] [BASE_URL]
LLM_MODEL_PARAM=${1:-"qwen3-32b-all-in-one"}
BASE_URL_PARAM="${2:-https://sd0qifhujhgnaj8ggfopg.apigateway-cn-shanghai.volceapi.com/}v1"

# 导出环境变量供子脚本使用
export LLM_MODEL="$LLM_MODEL_PARAM"
export BASE_URL="$BASE_URL_PARAM"

echo "使用 LLM_MODEL: $LLM_MODEL"
echo "使用 BASE_URL: $BASE_URL"

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_gaia-validation.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_gaia-validation-text-103.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_gaia-test.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_browsecomp-subset.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_simpleqa.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_webwalkerqa.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_hle.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_hle-text-500.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_frames.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_supergpqa.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_mmlu-pro.sh

bash scripts/qwen3-in-house/run_evaluate_multiple_runs_bbeh.sh

# 清除环境变量
unset LLM_MODEL
unset BASE_URL
