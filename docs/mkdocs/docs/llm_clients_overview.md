# LLM Clients Overview

## Available Clients

| Client | Provider | Model | Environment Variables |
|--------|----------|-------|---------------------|
| `ClaudeAnthropicClient` | Anthropic Direct | claude-3-7-sonnet | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` |
| `ClaudeOpenRouterClient` | OpenRouter | anthropic/claude-3.7-sonnet, and other [supported models](https://openrouter.ai/models) | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| `GPTOpenAIClient` | OpenAI | gpt-4, gpt-3.5 | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `MiroThinkerSGLangClient` | SGLang | MiroThinker series | `OAI_MIROTHINKER_API_KEY`, `OAI_MIROTHINKER_BASE_URL` |

## Basic Configuration
```yaml
main_agent:
  llm: 
    provider_class: "ClientName"
    model_name: "model-name"
    api_key_param: "${oc.env:API_KEY,???}"
    base_url_param: "${oc.env:BASE_URL,default-url}"
    ...
```

## Quick Start
1. Set relevant environment variable for your chosen provider
2. Update your yaml config file
3. Run: `uv run main.py trace --config_file_name=your_config_file --task="task" --task_file_name="file"`

---
**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI