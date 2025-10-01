# GAIA Validation Prerequisites

This document covers the common setup requirements and prerequisites for running GAIA validation benchmarks with MiroFlow, regardless of the specific model configuration used.

## About the GAIA Dataset

!!! info "What is GAIA?"
    GAIA (General AI Assistant) is a comprehensive benchmark designed to evaluate AI agents' ability to perform complex reasoning tasks that require multiple skills including web browsing, file manipulation, data analysis, and multi-step problem solving.

More details: [GAIA: a benchmark for General AI Assistants](https://arxiv.org/abs/2311.12983)

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

## Dataset Preparation

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

---

## Common API Keys Configuration

### Required API Keys

The following API keys are required for all GAIA validation runs, regardless of the model configuration:

```env title="Common .env Configuration"
# Search and web scraping capabilities
SERPER_API_KEY="your-serper-api-key"
JINA_API_KEY="your-jina-api-key"

# Code execution environment
E2B_API_KEY="your-e2b-api-key"

# Vision understanding capabilities
ANTHROPIC_API_KEY="your-anthropic-api-key"
GEMINI_API_KEY="your-gemini-api-key"

# LLM judge, reasoning, and hint generation
OPENAI_API_KEY="your-openai-api-key"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

### API Key Descriptions

- **SERPER_API_KEY**: Required for web search functionality
- **JINA_API_KEY**: Required for web scraping and content extraction
- **E2B_API_KEY**: Required for secure code execution environment
- **ANTHROPIC_API_KEY**: Required for vision understanding capabilities
- **GEMINI_API_KEY**: Required for additional vision processing
- **OPENAI_API_KEY**: Required for hint generation and final answer extraction

---

## Progress Monitoring and Resume

### Progress Tracking

You can monitor the evaluation progress in real-time:

```bash title="Check Progress"
uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
```

Replace `$PATH_TO_LOG` with your actual output directory path.

### Resume Capability

If the evaluation is interrupted, you can resume from where it left off by specifying the same output directory:

```bash title="Resume Interrupted Evaluation"
uv run main.py common-benchmark \
  --config_file_name=YOUR_CONFIG_FILE \
  output_dir="logs/gaia-validation/20250922_1430"
```

---

## Execution Traces

!!! info "Complete Execution Traces"
    We have released our complete execution traces for the `gaia-validation` dataset on Hugging Face. This comprehensive collection includes a full run of 165 tasks with detailed reasoning traces.

You can download them using the following command:

```bash title="Download Execution Traces"
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia_validation_miroflow_trace_public_20250825.zip
unzip gaia_validation_miroflow_trace_public_20250825.zip
# Unzip passcode: pf4*
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI
