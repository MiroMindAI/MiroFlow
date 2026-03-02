# WebWalkerQA

MiroFlow's evaluation on the WebWalkerQA benchmark demonstrates web navigation and question-answering capabilities across diverse domains.

More details: [WebWalkerQA on HuggingFace](https://huggingface.co/datasets/MiromindAI/WebWalkerQA)

---

## Dataset Overview

!!! abstract "Key Dataset Characteristics"

    - **Total Tasks**: 680 tasks in the main split
    - **Language**: English
    - **Domains**: Conference, game, academic, business, and more
    - **Task Types**: Web navigation, information retrieval, multi-hop reasoning
    - **Difficulty Levels**: Easy, medium, hard
    - **Evaluation**: Automated comparison with ground truth answers

---

## Quick Start Guide

### Step 1: Prepare the WebWalkerQA Dataset

```bash title="Download WebWalkerQA Dataset"
uv run -m miroflow.utils.prepare_benchmark.main get webwalkerqa
```

This will create the standardized dataset at `data/webwalkerqa/standardized_data.jsonl`.

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

```bash title="Run WebWalkerQA Evaluation with MiroThinker"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_webwalkerqa_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/webwalkerqa/$(date +"%Y%m%d_%H%M")"
```

For multiple runs:

```bash title="Run Multiple Evaluations (3 runs)"
bash scripts/benchmark/mirothinker/webwalkerqa_mirothinker_3runs.sh
```

!!! tip "Progress Monitoring and Resume"
    To check the progress while running:

    ```bash title="Check Progress"
    uv run utils/check_progress_webwalkerqa.py $PATH_TO_LOG
    ```

    If you need to resume an interrupted evaluation, specify the same output directory.

Results are automatically generated in the output directory:
- `benchmark_results.jsonl` - Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt` - Summary accuracy statistics

---

## Usage Examples

```bash title="Limited Task Testing"
# Test with 10 tasks only
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_webwalkerqa_mirothinker.yaml \
  benchmark.execution.max_tasks=10 \
  output_dir="logs/webwalkerqa/test"
```

```bash title="Custom Concurrency"
# Run with 10 concurrent tasks
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_webwalkerqa_mirothinker.yaml \
  benchmark.execution.max_concurrent=10 \
  output_dir="logs/webwalkerqa/$(date +"%Y%m%d_%H%M")"
```

---

## Available Configurations

| Config File | Model | Use Case |
|-------------|-------|----------|
| `benchmark_webwalkerqa_mirothinker.yaml` | MiroThinker | Standard evaluation |

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
