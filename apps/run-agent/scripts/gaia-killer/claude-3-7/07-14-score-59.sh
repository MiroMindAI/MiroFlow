# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

uv run python benchmarks/common_benchmark.py \
    benchmark=gaia-validation \
    llm.provider=anthropic \
    llm.model_name=claude-3-7-sonnet-20250219 \
    llm.async_client=true \
    benchmark.execution.max_concurrent=5 \
    benchmark.execution.pass_at_k=1 \
    agent=old_set