# OpenRouter Claude 3.7 Sonnet (Recommended)

Access multiple models via OpenRouter using unified OpenAI chat format. Supports Claude, GPT, and [other models](https://openrouter.ai/models) with higher rate limits.

## Client Used

`ClaudeOpenRouterClient`

## Environment Setup

```bash title="Environment Variables"
export OPENROUTER_API_KEY="your-openrouter-key"
export OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"  # optional
```

## Configuration

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "ClaudeOpenRouterClient"
    model_name: "anthropic/claude-3.7-sonnet"  # or openai/gpt-4, etc.
    async_client: true
    temperature: 0.3
    top_p: 0.95
    min_p: 0.0
    top_k: -1
    max_tokens: 32000
    openrouter_api_key: "${oc.env:OPENROUTER_API_KEY,???}"
    openrouter_base_url: "${oc.env:OPENROUTER_BASE_URL,https://openrouter.ai/api/v1}"
    openrouter_provider: "anthropic"  # Force provider, or "" for auto
    disable_cache_control: false
    keep_tool_result: -1
    oai_tool_thinking: false
```


## Usage

```bash title="Example Command"
# Run with Claude 3.7 Sonnet on example dataset
uv run main.py common-benchmark --config_file_name=agent_llm_claude37sonnet output_dir="logs/test"
```

The `agent_llm_claude37sonnet.yaml` configuration file provides a ready-to-use setup with the example dataset benchmark.

## Benefits vs Direct API

- Unified chat format
- Higher rate limits

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI