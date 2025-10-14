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
uv run main.py prepare-benchmark get browsecomp-test
```

This will create the standardized dataset at `data/browsecomp-test/standardized_data.jsonl`.

!!! warning "Requires HuggingFace Token"
    Add your HuggingFace token to `.env`: `HF_TOKEN="your_token_here"`

### Step 2: Configure API Keys

```env title=".env Configuration"
# Search and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# Code execution
E2B_API_KEY="xxx"

# LLM (Claude 3.7 Sonnet via OpenRouter)
OPENROUTER_API_KEY="xxx"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Evaluation and hint generation
OPENAI_API_KEY="xxx"

# Vision capabilities
ANTHROPIC_API_KEY="xxx"
GEMINI_API_KEY="xxx"
```

### Step 3: Run the Evaluation

```bash title="Run BrowseComp-EN Evaluation"
uv run main.py common-benchmark --config_file_name=agent_browsecomp-en_claude37sonnet benchmark=browsecomp-en output_dir="logs/browsecomp-en/$(date +"%Y%m%d_%H%M")"
```

Results are automatically generated in the output directory:
- `benchmark_results.jsonl` - Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt` - Summary accuracy statistics

---

## Usage Examples

```bash title="Limited Task Testing"
# Test with 10 tasks only
uv run main.py common-benchmark --config_file_name=agent_browsecomp-en_claude37sonnet benchmark=browsecomp-en benchmark.execution.max_tasks=10 output_dir="logs/browsecomp-en/$(date +"%Y%m%d_%H%M")"
```

```bash title="Using MiroThinker Model"
uv run main.py common-benchmark --config_file_name=agent_browsecomp-en_mirothinker benchmark=browsecomp-en output_dir="logs/browsecomp-en/$(date +"%Y%m%d_%H%M")"
```

---

## Available Agent Configurations

| Agent Configuration | Model | Use Case |
|-------------------|-------|----------|
| `agent_browsecomp-en_claude37sonnet` | Claude 3.7 Sonnet | Recommended for better performance |
| `agent_browsecomp-en_mirothinker` | MiroThinker | For local deployment |

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI

