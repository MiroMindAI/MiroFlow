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
uv run main.py prepare-benchmark get webwalkerqa
```

This will create the standardized dataset at `data/webwalkerqa/standardized_data.jsonl`.

### Step 2: Configure API Keys

=== "Claude 3.7 Sonnet"

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

=== "MiroThinker"

    ```env title=".env Configuration"
    # Search and web scraping
    SERPER_API_KEY="xxx"
    JINA_API_KEY="xxx"
    
    # Code execution
    E2B_API_KEY="xxx"
    
    # LLM (MiroThinker via SGLang)
    OAI_MIROTHINKER_API_KEY="dummy_key"
    OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"
    
    # Evaluation and final answer extraction
    OPENAI_API_KEY="xxx"
    
    # Vision capabilities
    ANTHROPIC_API_KEY="xxx"
    GEMINI_API_KEY="xxx"
    ```

### Step 3: Run the Evaluation

```bash title="Run WebWalkerQA Evaluation"
uv run main.py common-benchmark --config_file_name=agent_webwalkerqa_claude37sonnet output_dir="logs/webwalkerqa/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Progress Monitoring and Resume"
    To check the progress while running:
    
    ```bash title="Check Progress"
    ls -lh logs/webwalkerqa/YOUR_RUN_DIR/
    ```
    
    If you need to resume an interrupted evaluation, specify the same output directory:
    
    ```bash title="Resume Evaluation"
    uv run main.py common-benchmark --config_file_name=agent_webwalkerqa_claude37sonnet output_dir=${PATH_TO_LOG}
    ```

Results are automatically generated in the output directory:
- `benchmark_results.jsonl` - Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt` - Summary accuracy statistics

---

## Usage Examples

```bash title="Limited Task Testing"
# Test with 10 tasks only
uv run main.py common-benchmark --config_file_name=agent_webwalkerqa_claude37sonnet benchmark.execution.max_tasks=10 output_dir="logs/webwalkerqa/test"
```

```bash title="Custom Concurrency"
# Run with 10 concurrent tasks
uv run main.py common-benchmark --config_file_name=agent_webwalkerqa_claude37sonnet benchmark.execution.max_concurrent=10 output_dir="logs/webwalkerqa/$(date +"%Y%m%d_%H%M")"
```

```bash title="Using MiroThinker Model"
uv run main.py common-benchmark --config_file_name=agent_webwalkerqa_mirothinker output_dir="logs/webwalkerqa/$(date +"%Y%m%d_%H%M")"
```

---

## Available Agent Configurations

| Agent Configuration | Model | Use Case |
|-------------------|-------|----------|
| `agent_webwalkerqa_claude37sonnet` | Claude 3.7 Sonnet | Recommended for best performance |
| `agent_webwalkerqa_mirothinker` | MiroThinker | For local deployment |

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI

