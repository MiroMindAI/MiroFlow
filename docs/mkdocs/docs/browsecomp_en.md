# BrowseComp-EN (English)

MiroFlow's evaluation on the BrowseComp-EN benchmark demonstrates advanced web browsing and information retrieval capabilities.

More details: [BrowseComp: A Simple Yet Challenging Benchmark for Browsing Agents](https://arxiv.org/abs/2504.12516)

---

## Dataset Overview

!!! abstract "Key Dataset Characteristics"

    - **Total Tasks**: 1,266 tasks in the test split
    - **Language**: English
    - **Task Types**: Web browsing, search, and information retrieval
    - **Evaluation**: Automated comparison with ground truth answers

---

## Quick Start Guide

### Step 1: Prepare the BrowseComp-EN Dataset

```bash title="Download BrowseComp-EN Dataset"
uv run -m miroflow.utils.prepare_benchmark.main get browsecomp-test
```

This will create the standardized dataset at `data/browsecomp-test/standardized_data.jsonl`.

!!! warning "Requires HuggingFace Token"
    Add your HuggingFace token to `.env`: `HF_TOKEN="your_token_here"`

### Step 2: Configure API Keys

```env title=".env Configuration"
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# Search and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# Code execution
E2B_API_KEY="xxx"
```

### Step 3: Run the Evaluation

```bash title="Run BrowseComp-EN Evaluation with MiroThinker"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_browsecomp-en_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/browsecomp-en/$(date +"%Y%m%d_%H%M")"
```

For multiple runs:

```bash title="Run Multiple Evaluations (3 runs)"
bash scripts/benchmark/mirothinker/browsecomp-en_mirothinker_3runs.sh
```

Results are automatically generated in the output directory:
- `benchmark_results.jsonl` - Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt` - Summary accuracy statistics

---

## Usage Examples

```bash title="Limited Task Testing"
# Test with 10 tasks only
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_browsecomp-en_mirothinker.yaml \
  benchmark.execution.max_tasks=10 \
  output_dir="logs/browsecomp-en/$(date +"%Y%m%d_%H%M")"
```

```bash title="BrowseComp-EN-200 Subset (3 runs)"
bash scripts/benchmark/mirothinker/browsecomp-en-200_mirothinker_3runs.sh
```

---

## Available Configurations

| Config File | Model | Use Case |
|-------------|-------|----------|
| `benchmark_browsecomp-en_mirothinker.yaml` | MiroThinker | Full BrowseComp-EN evaluation |
| `benchmark_browsecomp-en-200_mirothinker.yaml` | MiroThinker | 200-task subset evaluation |

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
