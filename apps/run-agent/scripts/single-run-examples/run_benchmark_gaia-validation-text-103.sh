# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

uv run python benchmarks/common_benchmark.py \
benchmark=gaia-validation-text-103 \
llm.provider=qwen \
llm.model_name=qwen3-14b \
llm.openai_base_url=https://sd0qj642bmvj6f52jlqt0.apigateway-cn-shanghai.volceapi.com/v1 \
llm.top_p=0.9 \
llm.async_client=true \
benchmark.execution.max_tasks=5 \
benchmark.execution.max_concurrent=5 \
benchmark.execution.pass_at_k=5 \
agent=old_set

# for test purpose
# pricing.qwen.qwen3-14b.input_token_price=0.1 \
# pricing.qwen.qwen3-14b.output_token_price=0.1 ;

# # gpt-4.1
# uv run python benchmarks/common_benchmark.py \
# benchmark=gaia-validation-text-103 \
# llm=gpt-4.1 \
# llm.async_client=true \
# benchmark.execution.max_tasks=5 \
# benchmark.execution.max_concurrent=5 ;

# # claude 3.7 sonnet
# uv run python benchmarks/common_benchmark.py \
# benchmark=gaia-validation-text-103 \
# llm=claude \
# llm.async_client=true \
# llm.model_name=claude-3-7-sonnet-20250219 \
# benchmark.execution.max_tasks=5 \
# benchmark.execution.max_concurrent=5 ;

