# GAIA Validation - GPT5

MiroFlow now supports GPT-5 with MCP tool invocation, providing a unified workflow for multi-step reasoning, information integration, and scalable tool coordination.

!!! info "Prerequisites"
    Before proceeding, please review the [GAIA Validation Prerequisites](gaia_validation_prerequisites.md) document, which covers common setup requirements, dataset preparation, and API key configuration.

---

## Running the Evaluation

### Step 1: Dataset Preparation

Follow the [dataset preparation instructions](gaia_validation_prerequisites.md#dataset-preparation) in the prerequisites document.

### Step 2: API Keys Configuration

Configure the following API keys in your `.env` file:

```env title="GPT-5 .env Configuration"
# Search and web scraping capabilities
SERPER_API_KEY="your-serper-api-key"
JINA_API_KEY="your-jina-api-key"

# Code execution environment
E2B_API_KEY="your-e2b-api-key"

# Vision understanding capabilities
ANTHROPIC_API_KEY="your-anthropic-api-key"
GEMINI_API_KEY="your-gemini-api-key"

# Primary LLM provider, LLM judge, reasoning, and hint generation
OPENAI_API_KEY="your-openai-api-key"
OPENAI_BASE_URL="https://api.openai.com/v1"

```

### Step 3: Run the Evaluation

Execute the evaluation using the GPT-5 configuration:

```bash title="Run GAIA Validation with GPT-5"
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation-gpt5 \
  output_dir="logs/gaia-validation-gpt5/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress

Follow the [progress monitoring instructions](gaia_validation_prerequisites.md#progress-monitoring-and-resume) in the prerequisites document.


---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI