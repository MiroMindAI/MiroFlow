# OpenAI GPT-5

OpenAI's GPT-5 model with advanced reasoning capabilities and strong coding, vision, and problem-solving abilities.

## Client Configuration

**Client Class**: `GPT5OpenAIClient`

### Environment Setup

```bash title="Environment Variables"
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
```

### Agent Configuration

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "GPT5OpenAIClient"
    model_name: "gpt-5"
    async_client: true
    temperature: 1.0
    top_p: 1.0
    min_p: 0.0
    top_k: -1
    max_tokens: 16000
    reasoning_effort: "high" # Use high in the main agent, and use the default medium in the sub-agent.
    openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
    openai_base_url: "${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}"
```

### Usage

```bash title="Example Command"
# Run with GPT-5 on example dataset
uv run main.py common-benchmark --config_file_name=agent_llm_gpt5 output_dir="logs/test"
```

The `agent_llm_gpt5.yaml` configuration file provides a ready-to-use setup with the example dataset benchmark.

!!! tip "Reasoning Effort"
    GPT-5 supports the `reasoning_effort` parameter. The configuration uses `"high"` for better reasoning performance.

!!! tip "Sampling Parameters"
    While `min_p` and `top_k` are required in the configuration, OpenAI's API does not use them. Set them to `min_p: 0.0` and `top_k: -1` (disabled).

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI

