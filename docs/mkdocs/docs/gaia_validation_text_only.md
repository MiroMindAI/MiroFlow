# GAIA Validation Text-Only

The GAIA (General AI Assistant) benchmark is a comprehensive evaluation dataset designed to assess AI agents' capabilities in complex, real-world reasoning tasks. The text-only variant focuses specifically on tasks that can be completed using textual reasoning and web-based research, without requiring image or video processing capabilities.

More Details: [WebThinker: Empowering Large Reasoning Models with Deep Research Capability](https://arxiv.org/abs/2504.21776)

!!! warning "Evaluation Methodology"
    The text-only subset uses an LLM-as-judge evaluation approach, which differs from the exact-match evaluation used in GAIA-Validation or GAIA-Text. This methodology was established in the original WebThinker paper, and subsequent work should align with this approach for fair comparison.

---

## Setup and Evaluation Guide

### Step 1: Download the Dataset

Choose one of the following methods to obtain the GAIA Validation Text-Only dataset:

**Method 1: Automated Download (Recommended)**

```bash title="Download via MiroFlow Command"
uv run -m miroflow.utils.prepare_benchmark.main get gaia-val-text-only
```

**Method 2: Manual Download**

```bash title="Manual Dataset Download"
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-val-text-only.zip
unzip gaia-val-text-only.zip
# Unzip passcode: pf4*
```

### Step 2: Configure API Keys

!!! warning "Required API Configuration"
    Before running the evaluation, you must configure the necessary API keys in your `.env` file.

```env title="MiroThinker .env Configuration"
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

Execute the evaluation using the standard MiroThinker configuration:

```bash title="Run GAIA Validation Text-Only Evaluation"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_gaia-validation-text-103_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/gaia-validation-text-103/$(date +"%Y%m%d_%H%M")"
```

For multiple runs:

```bash title="Run Multiple Evaluations (8 runs)"
bash scripts/benchmark/mirothinker/gaia-validation-text-103_mirothinker_8runs.sh
```

### Step 4: Monitor Progress and Resume

!!! tip "Progress Tracking"
    You can monitor the evaluation progress in real-time using the progress checker:

```bash title="Check Evaluation Progress"
uv run utils/check_progress_gaia-validation-text-103.py $PATH_TO_LOG
```

Replace `$PATH_TO_LOG` with your actual output directory path.

!!! note "Resume Capability"
    If the evaluation is interrupted, you can resume from where it left off by specifying the same output directory:

```bash title="Resume Interrupted Evaluation"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_gaia-validation-text-103_mirothinker.yaml \
  output_dir="logs/gaia-validation-text-103/run_1"
```


---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
