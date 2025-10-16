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
uv run main.py prepare-benchmark get browsecomp-zh-test
```

This will create the standardized dataset at `data/browsecomp-zh-test/standardized_data.jsonl`.

### Step 2: Configure API Keys

```env title=".env Configuration"
# Search and web scraping (recommended for Chinese web)
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

# Optional: Set Chinese context mode
CHINESE_CONTEXT="true"
```

### Step 3: Run the Evaluation

```bash title="Run BrowseComp-ZH Evaluation"
uv run main.py common-benchmark --config_file_name=agent_browsecomp-zh_claude37sonnet output_dir="logs/browsecomp-zh/$(date +"%Y%m%d_%H%M")"
```

Results are automatically generated in the output directory:
- `benchmark_results.jsonl` - Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt` - Summary accuracy statistics

---

## Usage Examples

```bash title="Limited Task Testing"
# Test with 10 tasks only
uv run main.py common-benchmark --config_file_name=agent_browsecomp-zh_claude37sonnet benchmark.execution.max_tasks=10 output_dir="logs/browsecomp-zh/$(date +"%Y%m%d_%H%M")"
```

```bash title="Using MiroThinker Model"
uv run main.py common-benchmark --config_file_name=agent_browsecomp-zh_mirothinker output_dir="logs/browsecomp-zh/$(date +"%Y%m%d_%H%M")"
```

---

## Available Agent Configurations

| Agent Configuration | Model | Use Case |
|-------------------|-------|----------|
| `agent_browsecomp-zh_claude37sonnet` | Claude 3.7 Sonnet | Recommended for better performance on Chinese tasks |
| `agent_browsecomp-zh_mirothinker` | MiroThinker | For local deployment |

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI


