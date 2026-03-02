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
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# Search and web scraping capabilities
SERPER_API_KEY="your-serper-api-key"
JINA_API_KEY="your-jina-api-key"

# Code execution environment
E2B_API_KEY="your-e2b-api-key"
```

### Step 3: Run the Evaluation

Execute the evaluation using a standard configuration adapted for the GAIA test set:

```bash title="Run GAIA Test Evaluation"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_gaia-validation-165_mirothinker.yaml \
  benchmark=gaia-test \
  output_dir="logs/gaia-test/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress and Resume

!!! tip "Progress Tracking"
    You can monitor the evaluation progress in real-time:

```bash title="Check Progress"
uv run utils/check_progress_gaia-validation-165.py $PATH_TO_LOG
```

Replace `$PATH_TO_LOG` with your actual output directory path.

!!! note "Resume Capability"
    If the evaluation is interrupted, you can resume from where it left off by specifying the same output directory.

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
