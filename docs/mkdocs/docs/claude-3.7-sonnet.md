# Claude 3.7 Sonnet

Anthropic's Claude 3.7 Sonnet model with 200K context, strong reasoning, and tool use capabilities.

## Available Clients

### ClaudeAnthropicClient (Direct API)

**Environment Setup:**

```bash title="Environment Variables"
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"  # optional
```

**Configuration:**

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "ClaudeAnthropicClient"
    model_name: "claude-3-7-sonnet-20250219"  # Use actual model name from Anthropic API
    anthropic_api_key: "${oc.env:ANTHROPIC_API_KEY,???}"
    anthropic_base_url: "${oc.env:ANTHROPIC_BASE_URL,https://api.anthropic.com}"
```

## Usage

```bash title="Example Command"
# Use existing config
uv run main.py trace --config_file_name=your_config_file \
    --task="Your task" --task_file_name="data/file.txt"
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI