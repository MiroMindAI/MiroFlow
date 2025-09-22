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
    openrouter_api_key: "${oc.env:OPENROUTER_API_KEY,???}"
    openrouter_base_url: "${oc.env:OPENROUTER_BASE_URL,https://openrouter.ai/api/v1}"
    openrouter_provider: "anthropic"  # Force provider, or "" for auto
```

## Other Supported Models

- `openai/gpt-4`
- `openai/gpt-3.5-turbo`
- `anthropic/claude-3-opus`
- `google/gemini-pro`
- Many others via unified OpenAI format

## Usage

```bash title="Example Command"
# Use existing OpenRouter config
uv run main.py trace --config_file_name=your_config_file \
    --task="Your task" --task_file_name="data/file.txt"
```

## Benefits vs Direct API

- Unified chat format
- Higher rate limits

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI