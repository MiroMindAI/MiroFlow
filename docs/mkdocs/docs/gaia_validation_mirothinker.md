# GAIA Validation - MiroThinker

MiroFlow demonstrates state-of-the-art performance on the GAIA validation benchmark using MiroThinker models, showcasing exceptional capabilities in complex reasoning tasks that require multi-step problem solving, information synthesis, and tool usage.

!!! info "Prerequisites"
    Before proceeding, please review the [GAIA Validation Prerequisites](gaia_validation_prerequisites.md) document, which covers common setup requirements, dataset preparation, and API key configuration.

---

## Running the Evaluation

### Step 1: Dataset Preparation

Follow the [dataset preparation instructions](gaia_validation_prerequisites.md#dataset-preparation) in the prerequisites document.

### Step 2: API Keys Configuration

Configure the following API keys in your `.env` file:

```env title="MiroThinker .env Configuration"
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

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

# Hint Generation and final answer with MiroThinker model
HINT_LLM_BASE_URL="http://localhost:61005/v1"
FINAL_ANSWER_LLM_BASE_URL="http://localhost:61005/v1"

```

### Step 3: Run the Evaluation

Execute the evaluation using the MiroThinker configuration:

```bash title="Run GAIA Validation with MiroThinker"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation_mirothinker \
  output_dir="logs/gaia-validation-mirothinker/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress

Follow the [progress monitoring instructions](gaia_validation_prerequisites.md#progress-monitoring-and-resume) in the prerequisites document.

## Multiple Runs

Due to performance variance in MiroThinker models, it's recommended to run multiple evaluations for more reliable results.

```bash title="Run Multiple MiroThinker Evaluations"
bash ./scripts/run_evaluate_multiple_runs_mirothinker_gaia-validation.sh
```

This script runs 3 evaluations in parallel and calculates average scores. You can modify `NUM_RUNS` in the script to change the number of runs.

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI