# DeepSeek

DeepSeek's advanced language models with strong reasoning capabilities and tool use support, accessible via OpenRouter.

## Available Clients

### DeepSeekOpenRouterClient (OpenRouter API)

**Environment Setup:**

Set the `OPENROUTER_API_KEY` environment variable
```bash title="Environment Variables"
export OPENROUTER_API_KEY="your-key"
```
or add it to the `.env` file.

**Configuration:**

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "DeepSeekOpenRouterClient"
    model_name: "deepseek/deepseek-chat-v3.1"  # Available DeepSeek models via OpenRouter
    async_client: true
    temperature: 0.3
    top_p: 0.95
    min_p: 0.0
    top_k: -1
    max_tokens: 32000
    openrouter_api_key: "${oc.env:OPENROUTER_API_KEY,???}"
    openrouter_base_url: "${oc.env:OPENROUTER_BASE_URL,https://openrouter.ai/api/v1}"
    openrouter_provider: null # You can specify the provider to use
    disable_cache_control: false
    keep_tool_result: -1
    oai_tool_thinking: false
```

## Usage

```bash title="Example Command"
# Run with DeepSeek v3.1 Chat (OpenRouter) on example dataset
uv run main.py common-benchmark --config_file_name=agent_llm_deepseek_openrouter output_dir="logs/test"
```

The `agent_llm_deepseek_openrouter.yaml` configuration file provides a ready-to-use setup with the example dataset benchmark, while `agent_gaia-validation_deepseek.yaml` is an setup for the GAIA-Validation benchmark with main agent and sub agent configured.


---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
