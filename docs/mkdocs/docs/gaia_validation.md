# GAIA Validation

MiroFlow's performance on the GAIA validation benchmark demonstrates state-of-the-art capabilities in complex reasoning tasks.

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

## Reproduction Guide

!!! note "Reproducibility Instructions"
    This section provides step-by-step instructions to reproduce our GAIA validation benchmark results. All results are fully reproducible using our open-source framework.

### Step 1: Prepare the GAIA Validation Dataset

!!! tip "Dataset Setup"
    Please follow the Dataset Download Instructions from previous section.

Alternatively, you can manually download and set up the dataset as follows:

```bash title="Manual Dataset Download"
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-val.zip
unzip gaia-val.zip
# The unzip passcode is: `pf4*`
```


### Step 2: Configure API Keys

!!! warning "API Key Configuration"
    Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```env title=".env Configuration"
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

!!! example "Evaluation Execution"
    Execute the following command to run a single evaluation pass on the GAIA validation dataset:

```bash title="Run GAIA Validation"
uv run main.py common-benchmark --config_file_name=agent_gaia-validation output_dir="logs/gaia-validation/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Progress Monitoring and Resume"
    To check the progress while running:
    
    ```bash title="Check Progress"
    uv run uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
    ```
    If you need to resume an interrupted evaluation, specify the same output directory to continue from where you left off.

    ```bash title="Resume Evaluation, e.g."
    uv run main.py common-benchmark --config_file_name=agent_gaia-validation --output_dir="logs/gaia-validation/20251225_1430"
    ```

---

## Traces

!!! info "Complete Execution Traces"
    We have released our complete execution traces for the `gaia-validation` dataset on Hugging Face. This comprehensive collection includes a full run of 165 tasks with an overall accuracy of 73.94%.

You can download them using the following command:

```bash title="Download Execution Traces"
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia_validation_miroflow_trace_public_20250825.zip
unzip gaia_validation_miroflow_trace_public_20250825.zip
# The unzip passcode is: `pf4*`.
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI