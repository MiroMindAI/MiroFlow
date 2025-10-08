# LLM Clients Overview

MiroFlow supports multiple LLM providers through a unified client interface. Each client handles provider-specific API communication while maintaining consistent functionality.

## Available Clients

| Client | Provider | Model | Environment Variables |
|--------|----------|-------|---------------------|
| `ClaudeAnthropicClient` | Anthropic Direct | claude-3-7-sonnet | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` |
| `ClaudeOpenRouterClient` | OpenRouter | anthropic/claude-3.7-sonnet, and other [supported models](https://openrouter.ai/models) | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| `GPTOpenAIClient` | OpenAI | gpt-4, gpt-3.5 | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `GPT5OpenAIClient` | OpenAI | gpt-5 | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `MiroThinkerSGLangClient` | SGLang | MiroThinker series | `OAI_MIROTHINKER_API_KEY`, `OAI_MIROTHINKER_BASE_URL` |

## Basic Configuration

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "ClientName"
    model_name: "model-name"
    api_key_param: "${oc.env:API_KEY,???}"
    base_url_param: "${oc.env:BASE_URL,default-url}"
```

## Quick Setup

1. Set relevant environment variables for your chosen provider
2. Update your YAML config file with the appropriate client
3. Run: `uv run main.py trace --config_file_name=your_config_file --task="task"`

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI