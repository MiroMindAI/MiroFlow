# GAIA Validation

## Performance Comparison

MiroFlow achieves **state-of-the-art (SOTA) performance** among open-source agent frameworks on the GAIA validation set:


<div align="center">
  <img src="../assets/gaia_score.png" width="100%" alt="GAIA Validation Performance" />
</div>

**Key Performance Metrics:**

- **Pass@3**: **81.8%**
- **Majority Vote**: **82.4%**
- **Pass@1 (best@3)**: **74.5%**
- **Pass@1 (avg@3)**: **72.2%**

Unlike other frameworks with unclear evaluation methods, MiroFlow's results are **fully reproducible**. Note that Hugging Face access was disabled during inference to prevent direct answer retrieval

## Reproduction Guide

This section provides step-by-step instructions to reproduce our GAIA validation benchmark results. All results are fully reproducible using our open-source framework.

### Step 1: Prepare the GAIA Validation Dataset

Please follow the Dataset Download Instructions from previous section.

Alternatively, you can manually download and set up the dataset as follows:
```bash
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-val.zip
unzip gaia-val.zip
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

# We use Claude-3.5-Sonnet with OpenRouter backend to initialize the LLM. The main reason is that OpenRouter provides better response rates
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

Execute the following command to run a single evaluation pass on the GAIA validation dataset:

```
uv run main.py common-benchmark --config_file_name=agent_gaia-validation output_dir="logs/gaia-validation/$(date +"%Y%m%d_%H%M")"
```

To check the progress while running:
```
uv run uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
```


## Traces

We have released our complete execution traces for the `gaia-validation` dataset on Hugging Face. This comprehensive collection includes a full run of 165 tasks with an overall accuracy of 73.94%. You can download them using the following command:

```bash
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia_validation_miroflow_trace_public_20250825.zip
unzip gaia_validation_miroflow_trace_public_20250825.zip
# The unzip passcode is: `pf4*`.
```



---
**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI