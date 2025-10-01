# GAIA Validation - Claude 3.7 Sonnet

MiroFlow demonstrates state-of-the-art performance on the GAIA validation benchmark using Claude 3.7 Sonnet models, showcasing exceptional capabilities in complex reasoning tasks that require multi-step problem solving, information synthesis, and tool usage.

!!! info "Prerequisites"
    Before proceeding, please review the [GAIA Validation Prerequisites](gaia_validation_prerequisites.md) document, which covers common setup requirements, dataset preparation, and API key configuration.

---

## Performance Comparison

!!! success "State-of-the-Art Performance with Claude 3.7 Sonnet"
    MiroFlow achieves **state-of-the-art (SOTA) performance** among open-source agent frameworks on the GAIA validation set using Claude 3.7 Sonnet.

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

## Running the Evaluation

### Step 1: Dataset Preparation

Follow the [dataset preparation instructions](gaia_validation_prerequisites.md#dataset-preparation) in the prerequisites document.

### Step 2: API Keys Configuration

Configure the following API keys in your `.env` file:

```env title="Claude 3.7 Sonnet .env Configuration"
# Primary LLM provider (Claude-3.7-Sonnet via OpenRouter)
OPENROUTER_API_KEY="your-openrouter-api-key"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

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

### Step 3: Run the Evaluation

Execute the evaluation using the Claude 3.7 Sonnet configuration:

```bash title="Run GAIA Validation with Claude 3.7 Sonnet"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation_claude37sonnet \
  output_dir="logs/gaia-validation-claude37sonnet/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress

Follow the [progress monitoring instructions](gaia_validation_prerequisites.md#progress-monitoring-and-resume) in the prerequisites document.

---

## Execution Traces

!!! info "Complete Execution Traces"
    We have released our complete execution traces for the `gaia-validation` dataset using Claude 3.7 Sonnet on Hugging Face. This comprehensive collection includes a full run of 165 tasks with an overall accuracy of 73.94% and detailed reasoning traces.

You can download them using the following command:

```bash title="Download Execution Traces"
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia_validation_miroflow_trace_public_20250825.zip
unzip gaia_validation_miroflow_trace_public_20250825.zip
# Unzip passcode: pf4*
```

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI