# HLE

MiroFlow's evaluation on the HLE-text-only benchmark demonstrates capabilities in multimodal reasoning and question answering tasks that require human-level understanding across vision and language.

More details: [HLE text only Dataset on HuggingFace](https://huggingface.co/datasets/macabdul9/hle_text_only)

---

## Dataset Overview

!!! info "HLE Dataset (text only)"
    The dataset is a text-only subset of HLE. 

---

## Quick Start Guide

### Step 1: Prepare the HLE(text only) Dataset

```bash title="Download HLE(text only) Dataset"
uv run main.py prepare-benchmark get hle-text-only
```

This will download the dataset to `data/hle-text-only/`.

### Step 2: Configure API Keys

```env title=".env Configuration"
# For searching and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# For Linux sandbox (code execution environment)
E2B_API_KEY="xxx"

# Claude-3.7-Sonnet via OpenRouter
OPENROUTER_API_KEY="xxx"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Vision understanding
ANTHROPIC_API_KEY="xxx"
GEMINI_API_KEY="xxx"

# Hint generation and final answer extraction
OPENAI_API_KEY="xxx"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

### Step 3: Run the Evaluation

```bash title="Run HLE Evaluation"
uv run main.py common-benchmark --config_file_name=agent_hle-text-only_claude37sonnet output_dir="logs/hle-text-only/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Resume Interrupted Evaluation"
    Specify the same output directory to continue from where you left off:
    
    ```bash
    uv run main.py common-benchmark --config_file_name=agent_hle-text-only_claude37sonnet output_dir="logs/hle-text-only/20251014_1504"
    ```

### Step 4: Review Results

```bash title="Check Results"
# View accuracy summary
cat logs/hle-text-only/*/benchmark_results_pass_at_1_accuracy.txt

# View detailed results
cat logs/hle-text-only/*/benchmark_results.jsonl
```

---

## Usage Examples

### Test with Limited Tasks

```bash
uv run main.py common-benchmark --config_file_name=agent_hle-text-only_claude37sonnet benchmark.execution.max_tasks=10 output_dir="logs/hle-text-only/$(date +"%Y%m%d_%H%M")"
```

### Adjust Concurrency

```bash
uv run main.py common-benchmark --config_file_name=agent_hle-text-only_claude37sonnet benchmark.execution.max_concurrent=5 output_dir="logs/hle-text-only/$(date +"%Y%m%d_%H%M")"
```

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI

