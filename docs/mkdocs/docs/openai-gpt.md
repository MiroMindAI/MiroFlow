# OpenAI GPT Models

OpenAI's latest models including GPT-5, GPT-4o and advanced reasoning models with strong coding, vision, and reasoning capabilities.

## Client Used for GPT-5

`GPT5OpenAIClient`

### Environment Setup

```bash title="Environment Variables"
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
```

### Configuration

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
    max_tokens: 128000
    reasoning_effort: "high" # Use high in the main agent, and use the default medium in the sub-agent.
    openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
    openai_base_url: "${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}"
```

### Usage

```bash title="Example Command"
# Create custom OpenAI config
uv run main.py trace --config_file_name=your_config_file \
    --task="Your task" --task_file_name="data/file.txt"
```

## Client Used for GPT-4o

`GPTOpenAIClient`

### Environment Setup

```bash title="Environment Variables"
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
```

### Configuration

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "GPTOpenAIClient"
    model_name: "gpt-4o"  # or gpt-4o-mini, etc.
    openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
    openai_base_url: "${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}"
```

### Usage

```bash title="Example Command"
# Create custom OpenAI config
uv run main.py trace --config_file_name=your_config_file \
    --task="Your task" --task_file_name="data/file.txt"
```

!!! note "Configuration Notes"
    - `GPTOpenAIClient` also supports GPT-5, but it has not been fully validated on MiroFlow yet. We recommend using `GPT5OpenAIClient`.

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI