# HLE Text-Only

MiroFlow's evaluation on the HLE-text-only benchmark demonstrates capabilities in reasoning and question answering tasks that require human-level understanding.

More details: [HLE text only Dataset on HuggingFace](https://huggingface.co/datasets/macabdul9/hle_text_only)

---

## Dataset Overview

!!! info "HLE Dataset (text only)"
    The experiments are conducted on the **500 text-only subset** of the HLE dataset, available from [WebThinker](https://github.com/RUC-NLPIR/WebThinker/blob/main/data/HLE/test.json).

---

## Quick Start Guide

### Step 1: Prepare the HLE (text only) Dataset

```bash title="Download HLE (text only) Dataset"
uv run -m src.utils.prepare_benchmark.main get hle-text-only
```

This will download the dataset to `data/hle-text-only/`.

### Step 2: Configure API Keys

```env title=".env Configuration"
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# For searching and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# For code execution (E2B sandbox)
E2B_API_KEY="xxx"
```

### Step 3: Run the Evaluation

```bash title="Run HLE Text-Only Evaluation with MiroThinker"
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_hle-text-only_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/hle-text-only/$(date +"%Y%m%d_%H%M")"
```

For multiple runs:

```bash title="Run Multiple Evaluations (3 runs)"
bash scripts/standard_hle-text-only_mirothinker_3runs.sh
```

!!! tip "Resume Interrupted Evaluation"
    Specify the same output directory to continue from where you left off.

### Step 4: Review Results

```bash title="Check Results"
# View accuracy summary
cat logs/hle-text-only/*/benchmark_results_pass_at_1_accuracy.txt

# Check progress
uv run utils/check_progress_hle-text-only.py $PATH_TO_LOG
```

---

## Usage Examples

### Test with Limited Tasks

```bash
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_hle-text-only_mirothinker.yaml \
  benchmark.execution.max_tasks=10 \
  output_dir="logs/hle-text-only/$(date +"%Y%m%d_%H%M")"
```

### Adjust Concurrency

```bash
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_hle-text-only_mirothinker.yaml \
  benchmark.execution.max_concurrent=5 \
  output_dir="logs/hle-text-only/$(date +"%Y%m%d_%H%M")"
```

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
