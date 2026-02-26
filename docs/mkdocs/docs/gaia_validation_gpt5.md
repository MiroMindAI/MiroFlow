# GAIA Validation - GPT-5

MiroFlow supports GPT-5 with MCP tool invocation, providing a unified workflow for multi-step reasoning, information integration, and scalable tool coordination.

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

!!! note "Configuration Note"
    To run with GPT-5, create a custom config based on the standard configs with a GPT-5 LLM provider (`GPT5OpenAIClient`). See [YAML Configuration Guide](yaml_config.md) for details on creating custom configurations.

### Step 4: Monitor Progress

Follow the [progress monitoring instructions](gaia_validation_prerequisites.md#progress-monitoring-and-resume) in the prerequisites document.


---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
