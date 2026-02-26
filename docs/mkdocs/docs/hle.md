# HLE

MiroFlow's evaluation on the HLE benchmark demonstrates capabilities in multimodal reasoning and question answering tasks that require human-level understanding across vision and language.

More details: [Humanity's Last Exam](https://arxiv.org/abs/2501.14249)

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
uv run -m src.utils.prepare_benchmark.main get hle
```

This will download the dataset and save images to `data/hle/images/`.

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

```bash title="Run HLE Evaluation with MiroThinker"
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_hle_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/hle/$(date +"%Y%m%d_%H%M")"
```

For multiple runs:

```bash title="Run Multiple Evaluations (3 runs)"
bash scripts/standard_hle_mirothinker_3runs.sh
```

!!! tip "Resume Interrupted Evaluation"
    Specify the same output directory to continue from where you left off.

### Step 4: Review Results

```bash title="Check Results"
# View accuracy summary
cat logs/hle/*/benchmark_results_pass_at_1_accuracy.txt

# Check progress
uv run utils/check_progress_hle.py $PATH_TO_LOG
```

---

## Usage Examples

### Test with Limited Tasks

```bash
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_hle_mirothinker.yaml \
  benchmark.execution.max_tasks=10 \
  output_dir="logs/hle/$(date +"%Y%m%d_%H%M")"
```

### Adjust Concurrency

```bash
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_hle_mirothinker.yaml \
  benchmark.execution.max_concurrent=5 \
  output_dir="logs/hle/$(date +"%Y%m%d_%H%M")"
```

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
