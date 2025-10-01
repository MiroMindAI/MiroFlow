# GAIA Test

The GAIA (General AI Assistant) test set provides a comprehensive evaluation dataset for assessing AI agents' capabilities in complex, real-world reasoning tasks. This benchmark tests agents' ability to perform multi-step problem solving, information synthesis, and tool usage across diverse scenarios.

More details: [GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)


---

## Setup and Evaluation Guide

### Step 1: Download the GAIA Test Dataset

**Direct Download (Recommended)**

```bash
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-test.zip
unzip gaia-test.zip
# Unzip passcode: pf4*
```

### Step 2: Configure API Keys

!!! warning "Required API Configuration"
    Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```env title=".env Configuration"
# Search and web scraping capabilities
SERPER_API_KEY="your-serper-api-key"
JINA_API_KEY="your-jina-api-key"

# Code execution environment
E2B_API_KEY="your-e2b-api-key"

# Primary LLM provider (Claude-3.7-Sonnet via OpenRouter)
OPENROUTER_API_KEY="your-openrouter-api-key"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Vision understanding capabilities
ANTHROPIC_API_KEY="your-anthropic-api-key"
GEMINI_API_KEY="your-gemini-api-key"

# LLM judge, reasoning, and hint generation
OPENAI_API_KEY="your-openai-api-key"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

### Step 3: Run the Evaluation

Execute the evaluation using the following command:

```bash title="Run GAIA Test Evaluation"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-test \
  output_dir="logs/gaia-test/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress and Resume

!!! tip "Progress Tracking"
    You can monitor the evaluation progress in real-time:

```bash title="Check Progress"
uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
```

Replace `$PATH_TO_LOG` with your actual output directory path.

!!! note "Resume Capability"
    If the evaluation is interrupted, you can resume from where it left off by specifying the same output directory:

```bash title="Resume Interrupted Evaluation"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-test \
  output_dir="logs/gaia-test/20250922_1430"
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI