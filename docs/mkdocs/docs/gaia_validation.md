# GAIA Validation

MiroFlow demonstrates state-of-the-art performance on the GAIA validation benchmark, showcasing exceptional capabilities in complex reasoning tasks that require multi-step problem solving, information synthesis, and tool usage.

More details: [GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)

## About the GAIA Dataset

!!! info "What is GAIA?"
    GAIA (General AI Assistant) is a comprehensive benchmark designed to evaluate AI agents' ability to perform complex reasoning tasks that require multiple skills including web browsing, file manipulation, data analysis, and multi-step problem solving.

---

## Performance Comparison

!!! success "State-of-the-Art Performance"
    MiroFlow achieves **state-of-the-art (SOTA) performance** among open-source agent frameworks on the GAIA validation set.

<div align="center" markdown="1">
  ![GAIA Validation Performance](../assets/gaia_score.png){ width="100%" }
</div>

!!! abstract "Key Performance Metrics"
    - **Pass@3**: **81.8%**
    - **Majority Vote**: **82.4%**
    - **Pass@1 (best@3)**: **74.5%**
    - **Pass@1 (avg@3)**: **72.2%**

!!! info "Reproducibility Guarantee"
    Unlike other frameworks with unclear evaluation methods, MiroFlow's results are **fully reproducible**. Note that Hugging Face access was disabled during inference to prevent direct answer retrieval.

---

## Setup and Evaluation Guide

!!! note "Complete Reproduction Instructions"
    This section provides comprehensive step-by-step instructions to reproduce our GAIA validation benchmark results. All results are fully reproducible using our open-source framework.

### Step 1: Prepare the GAIA Validation Dataset

Choose one of the following methods to obtain the GAIA validation dataset:

**Method 1: Direct Download (Recommended)**

!!! tip "No Authentication Required"
    This method does not require HuggingFace tokens or access permissions.

```bash title="Manual Dataset Download"
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-val.zip
unzip gaia-val.zip
# Unzip passcode: pf4*
```

**Method 2: Using the prepare-benchmark command**

!!! warning "Prerequisites Required"
    This method requires HuggingFace dataset access and token configuration.

First, you need to request access and configure your environment:

1. **Request Dataset Access**: Visit [https://huggingface.co/datasets/gaia-benchmark/GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA) and request access
2. **Configure Environment**: 
   ```bash
   cp .env.template .env
   ```
   Edit the `.env` file:
   ```env
   HF_TOKEN="your-actual-huggingface-token-here"
   DATA_DIR="data/"
   ```

!!! tip "Getting Your Hugging Face Token"
    1. Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    2. Create a new token with at least "Read" permissions
    3. Add your token to the `.env` file

Then download the dataset:

```bash title="Download via Script"
uv run main.py prepare-benchmark get gaia-val
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

# LLM judge, reasoning, and O3 hints
OPENAI_API_KEY="your-openai-api-key"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

!!! tip "Why OpenRouter?"
    We use Claude-3.7-Sonnet through the OpenRouter backend as the primary LLM provider because OpenRouter offers better response rates and improved reliability compared to direct API access.

### Step 3: Run the Evaluation

Execute the evaluation using the following command:

```bash title="Run GAIA Validation"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation \
  output_dir="logs/gaia-validation/$(date +"%Y%m%d_%H%M")"
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
  --config_file_name=agent_gaia-validation \
  output_dir="logs/gaia-validation/20250922_1430"
```

---

## Execution Traces

!!! info "Complete Execution Traces"
    We have released our complete execution traces for the `gaia-validation` dataset on Hugging Face. This comprehensive collection includes a full run of 165 tasks with an overall accuracy of 73.94%.

You can download them using the following command:

```bash title="Download Execution Traces"
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia_validation_miroflow_trace_public_20250825.zip
unzip gaia_validation_miroflow_trace_public_20250825.zip
# Unzip passcode: pf4*
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI