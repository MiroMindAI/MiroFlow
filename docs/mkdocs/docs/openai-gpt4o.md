# OpenAI GPT-4o

OpenAI's GPT-4o model with multimodal capabilities, strong reasoning, and efficient performance.

## Client Configuration

**Client Class**: `GPTOpenAIClient`

### Environment Setup

```bash title="Environment Variables"
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
```

### Agent Configuration

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "GPTOpenAIClient"
    model_name: "gpt-4o"  # or gpt-4o-mini
    async_client: true
    temperature: 0.7
    top_p: 1.0
    min_p: 0.0
    top_k: -1
    max_tokens: 16000
    openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
    openai_base_url: "${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}"
```

### Usage

```bash title="Example Command"
# Run with GPT-4o on example dataset
uv run main.py common-benchmark --config_file_name=agent_llm_gpt4o output_dir="logs/test"
```

The `agent_llm_gpt4o.yaml` configuration file provides a ready-to-use setup with the example dataset benchmark.

!!! note "Available Models"
    The `GPTOpenAIClient` supports multiple GPT-4o variants:
    - `gpt-4o` - Full GPT-4o model
    - `gpt-4o-mini` - Smaller, faster variant

!!! warning "GPT-5 Support"
    `GPTOpenAIClient` also supports GPT-5, but it has not been fully validated on MiroFlow yet. We recommend using `GPT5OpenAIClient` for GPT-5.

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI

