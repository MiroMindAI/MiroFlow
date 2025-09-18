# GAIA Test

This document provides step-by-step instructions for evaluating the GAIA test benchmark.

### Step 1: Prepare the GAIA Test Dataset

First, download and prepare the GAIA test dataset:
```bash
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-test.zip
unzip gaia-test.zip
# The unzip passcode is: `pf4*`
```

### Step 2: Configure API Keys

Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```

# For searching and scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# For Linux sandbox (code execution environment)
E2B_API_KEY="xxx"

# We use Claude-3.7-Sonnet with OpenRouter backend to initialize the LLM. The main reason is that OpenRouter provides better response rates
OPENROUTER_API_KEY="xxx"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Used for Claude vision understanding
ANTHROPIC_API_KEY="xxx"

# Used for Gemini vision
GEMINI_API_KEY="xxx"

# Use for llm judge, reasoning, o3 hints, etc.
OPENAI_API_KEY="xxx"
OPENAI_BASE_URL="https://api.openai.com/v1"


```

### Step 3: Run the Evaluation

Execute the following command to run a single evaluation pass on the GAIA test dataset:

```
uv run main.py common-benchmark --config_file_name=agent_gaia-test output_dir="logs/gaia-test/$(date +"%Y%m%d_%H%M")"
```

---
**Last Updated:** Sep 2025  
**Doc Contributor:** Index @ MiroMind AI