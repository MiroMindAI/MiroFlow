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
    async_client: true
    temperature: 0.3
    top_p: 0.95
    min_p: 0.0
    top_k: -1
    max_tokens: 32000
    anthropic_api_key: "${oc.env:ANTHROPIC_API_KEY,???}"
    anthropic_base_url: "${oc.env:ANTHROPIC_BASE_URL,https://api.anthropic.com}"
    disable_cache_control: false
    keep_tool_result: -1
    oai_tool_thinking: false
```

!!! tip "Sampling Parameters"
    - `min_p` and `top_k` are required in the configuration
    - Anthropic API natively supports `top_k`, but `min_p` is not used by the API
    - Set `min_p: 0.0` (disabled) and `top_k: -1` (disabled) or a specific value like `top_k: 40`

## Usage

```bash title="Example Command"
# Run with Claude 3.7 Sonnet (Anthropic SDK) on example dataset
uv run main.py common-benchmark --config_file_name=agent_llm_claude37sonnet_anthropic output_dir="logs/test"
```

The `agent_llm_claude37sonnet_anthropic.yaml` configuration file provides a ready-to-use setup with the example dataset benchmark.

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI