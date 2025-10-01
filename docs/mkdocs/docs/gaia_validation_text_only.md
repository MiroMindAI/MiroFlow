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
uv run main.py prepare-benchmark get gaia-val-text-only
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
    Before running the evaluation, you must configure the necessary API keys in your `.env` file. Each service serves a specific purpose in the evaluation pipeline.

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

!!! tip "Why OpenRouter?"
    We use Claude-3.7-Sonnet through the OpenRouter backend as the primary LLM provider because OpenRouter offers better response rates and improved reliability compared to direct API access.

### Step 3: Run the Evaluation

Execute the evaluation using the following command structure:

```bash title="Run GAIA Validation Text-Only Evaluation"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation-text-only \
  output_dir="logs/gaia-validation-text-only/$(date +"%Y%m%d_%H%M")"
```



### Step 4: Monitor Progress and Resume

!!! tip "Progress Tracking"
    You can monitor the evaluation progress in real-time using the progress checker:

```bash title="Check Evaluation Progress"
uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
```

Replace `$PATH_TO_LOG` with your actual output directory path.

!!! note "Resume Capability"
    If the evaluation is interrupted, you can resume from where it left off by specifying the same output directory:

```bash title="Resume Interrupted Evaluation"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation-text-only \
  output_dir="logs/gaia-validation-text-only/20250922_1430"
```


---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI