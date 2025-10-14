# HLE

MiroFlow's evaluation on the HLE benchmark demonstrates capabilities in multimodal reasoning and question answering tasks that require human-level understanding across vision and language.

More details: [HLE Dataset on HuggingFace](https://huggingface.co/datasets/cais/hle)

---

## Dataset Overview

!!! info "HLE Dataset"
    The HLE dataset consists of challenging multimodal tasks that test AI systems' ability to perform human-level reasoning with both visual and textual information.

!!! abstract "Key Dataset Characteristics"

    - **Total Tasks**: Test split from HuggingFace `cais/hle` dataset
    - **Task Type**: Multimodal question answering and reasoning
    - **Modalities**: Text + Images
    - **Ground Truth**: Available for evaluation

---

## Quick Start Guide

### Step 1: Prepare the HLE Dataset

```bash title="Download HLE Dataset"
uv run main.py prepare-benchmark get hle
```

This will download the dataset and save images to `data/hle/images/`.

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
uv run main.py common-benchmark --config_file_name=agent_hle_claude37sonnet output_dir="logs/hle/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Resume Interrupted Evaluation"
    Specify the same output directory to continue from where you left off:
    
    ```bash
    uv run main.py common-benchmark --config_file_name=agent_hle_claude37sonnet output_dir="logs/hle/20251014_1504"
    ```

### Step 4: Review Results

```bash title="Check Results"
# View accuracy summary
cat logs/hle/*/benchmark_results_pass_at_1_accuracy.txt

# View detailed results
cat logs/hle/*/benchmark_results.jsonl
```

---

## Usage Examples

### Test with Limited Tasks

```bash
uv run main.py common-benchmark --config_file_name=agent_hle_claude37sonnet benchmark.execution.max_tasks=10 output_dir="logs/hle/$(date +"%Y%m%d_%H%M")"
```

### Adjust Concurrency

```bash
uv run main.py common-benchmark --config_file_name=agent_hle_claude37sonnet benchmark.execution.max_concurrent=5 output_dir="logs/hle/$(date +"%Y%m%d_%H%M")"
```

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI

