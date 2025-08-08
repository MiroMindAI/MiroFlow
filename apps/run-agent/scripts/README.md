# Benchmark Evaluation Scripts

This directory contains scripts for evaluating language models on various benchmarks.

## Data Download

Download evaluation datasets:

```bash
# Download and extract evaluation data
https://huggingface.co/datasets/miromind-ai/eval_data/resolve/main/eval_data.zip
```

The data should be placed in `mirage/data/` directory.

## Usage Examples

### 1. Single Dataset Evaluation

Run a single evaluation on GAIA validation dataset:

```bash
# Example: GAIA validation with Claude
uv run python benchmarks/common_benchmark.py \
    benchmark=gaia-validation \
    llm.provider=anthropic \
    llm.model_name=claude-3-7-sonnet-20250219 \
    llm.async_client=true \
    benchmark.execution.max_concurrent=5 \
    benchmark.execution.pass_at_k=1 \
    agent=old_set
```

**Script**: `scripts/single-run-examples/run_benchmark_gaia-validation.sh`

### 2. Multi-Run Statistical Analysis

Run multiple evaluations and calculate average performance:

This will:
- Launch 8 parallel evaluation runs
- Calculate average, std dev, min/max scores
- Save results to `logs/gaia-validation/{model}/average_scores_pass_at_1.txt`

**Script**: `scripts/qwen3-in-house/run_evaluate_multiple_runs_gaia-validation.sh`

### 3. Results

Single run output:
```
Pass@1 Accuracy e.g.: 45.00%
```

Multi-run output:
```
EVALUATION RESULTS e.g.
==================================================
Pass@1 Results:
Number of runs: 3
Individual scores: ['42.42%', '41.50%', '43.20%']
Average score: 42.37%
==================================================
```

## Configuration

Key parameters:
- `benchmark`: Dataset name (`gaia-validation`, `simpleqa`, `mmlu-pro`)
- `llm.provider`: LLM provider (`anthropic`, `openai`, `qwen`)
- `llm.model_name`: Model identifier
- `benchmark.execution.max_concurrent`: Parallel tasks (default: 10)
- `benchmark.execution.pass_at_k`: Pass@k evaluation (default: 1)
- `agent`: Agent setting name (e.g. `old_set`, `owl_set`, `owl_set_owl_frame`)
- etc.
