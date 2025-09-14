# Claude 3.7 Sonnet

## What This Is
Anthropic's Claude 3.7 Sonnet model with 200K context, strong reasoning, and tool use capabilities.

## Available Clients

### ClaudeAnthropicClient (Direct API)
**Environment:**
```bash
export ANTHROPIC_API_KEY="your-key"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"  # optional
```

**Config:**
```yaml
main_agent:
  llm: 
    provider_class: "ClaudeAnthropicClient"
    model_name: "claude-3-7-sonnet-20250219"  # Use actual model name from Anthropic API
    anthropic_api_key: "${oc.env:ANTHROPIC_API_KEY,???}"
    anthropic_base_url: "${oc.env:ANTHROPIC_BASE_URL,https://api.anthropic.com}"
    ...
```

## Usage
```bash
# Use existing config
uv run main.py trace --config_file_name=your_config_file \
    --task="Your task" --task_file_name="data/file.txt"
```



---
**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI