# BrowseComp-ZH (Chinese)

MiroFlow's evaluation on the BrowseComp-ZH benchmark demonstrates advanced web browsing and information retrieval capabilities in the Chinese information ecosystem.

More details: [BrowseComp-ZH: Benchmarking Web Browsing Ability of Large Language Models in Chinese](https://github.com/PALIN2018/BrowseComp-ZH)

---

## Dataset Overview

!!! abstract "Key Dataset Characteristics"

    - **Total Tasks**: 289 complex multi-hop retrieval questions in the test split
    - **Language**: Chinese (Simplified)
    - **Task Types**: Web browsing, search, and information retrieval with multi-hop reasoning
    - **Domains**: 11 domains including Film & TV, Technology, Medicine, History, Sports, and Arts
    - **Evaluation**: Automated comparison with ground truth answers
    - **Difficulty**: High-difficulty benchmark designed to test real-world Chinese web browsing capabilities

---

## Quick Start Guide

### Step 1: Prepare the BrowseComp-ZH Dataset

```bash title="Download BrowseComp-ZH Dataset"
uv run -m src.utils.prepare_benchmark.main get browsecomp-zh-test
```

This will create the standardized dataset at `data/browsecomp-zh-test/standardized_data.jsonl`.

### Step 2: Configure API Keys

```env title=".env Configuration"
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# Search and web scraping (recommended for Chinese web)
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# Code execution
E2B_API_KEY="xxx"

# Optional: Set Chinese context mode
CHINESE_CONTEXT="true"
```

### Step 3: Run the Evaluation

```bash title="Run BrowseComp-ZH Evaluation with MiroThinker"
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_browsecomp-zh_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/browsecomp-zh/$(date +"%Y%m%d_%H%M")"
```

For multiple runs:

```bash title="Run Multiple Evaluations (3 runs)"
bash scripts/standard_browsecomp-zh_mirothinker_3runs.sh
```

Results are automatically generated in the output directory:
- `benchmark_results.jsonl` - Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt` - Summary accuracy statistics

---

## Usage Examples

```bash title="Limited Task Testing"
# Test with 10 tasks only
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_browsecomp-zh_mirothinker.yaml \
  benchmark.execution.max_tasks=10 \
  output_dir="logs/browsecomp-zh/$(date +"%Y%m%d_%H%M")"
```

```bash title="Using Sogou Search (alternative)"
bash scripts/standard_browsecomp-zh_mirothinker_sogou_3runs.sh
```

---

## Available Configurations

| Config File | Model | Use Case |
|-------------|-------|----------|
| `standard_browsecomp-zh_mirothinker.yaml` | MiroThinker | Standard Chinese web evaluation |
| `standard_browsecomp-zh_mirothinker_sogou.yaml` | MiroThinker | With Sogou search for Chinese content |

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
