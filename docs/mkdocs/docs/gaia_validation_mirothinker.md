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
```

### Step 3: Run the Evaluation

Execute the evaluation using the MiroThinker standard configuration:

```bash title="Run GAIA Validation with MiroThinker"
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_gaia-validation-165_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/gaia-validation-165/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress

Follow the [progress monitoring instructions](gaia_validation_prerequisites.md#progress-monitoring-and-resume) in the prerequisites document.

## Multiple Runs

Due to performance variance in MiroThinker models, it's recommended to run multiple evaluations for more reliable results.

```bash title="Run Multiple MiroThinker Evaluations (8 runs)"
bash scripts/standard_gaia-validation-165_mirothinker_8runs.sh
```

This script runs 8 evaluations in parallel and calculates average scores. You can modify `NUM_RUNS` in the script to change the number of runs.

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
