# LLM Clients Overview

MiroFlow supports multiple LLM providers through a unified client interface. Each client handles provider-specific API communication while maintaining consistent functionality.

## Available Clients

| Client | Provider | Model | Environment Variables |
|--------|----------|-------|---------------------|
| `ClaudeAnthropicClient` | Anthropic Direct | claude-3-7-sonnet | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` |
| `ClaudeOpenRouterClient` | OpenRouter | anthropic/claude-3.7-sonnet, and other [supported models](https://openrouter.ai/models) | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| `GPTOpenAIClient` | OpenAI | gpt-4o, gpt-4o-mini | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `GPT5OpenAIClient` | OpenAI | gpt-5 | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `OpenRouterClient` | OpenRouter | Any model on OpenRouter | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| `OpenAIClient` | OpenAI-Compatible | Any OpenAI-compatible model | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `MiroThinkerSGLangClient` | SGLang | MiroThinker series | `OAI_MIROTHINKER_API_KEY`, `OAI_MIROTHINKER_BASE_URL` |

## Basic Configuration

```yaml title="Agent Configuration"
main_agent:
  llm:
    _base_: config/llm/base_mirothinker.yaml   # or base_openai.yaml
    provider_class: "MiroThinkerSGLangClient"
    model_name: "mirothinker-v1.5"
```

## LLM Base Configs

Pre-configured base configurations are available in `config/llm/`:

| Config File | Provider | Description |
|-------------|----------|-------------|
| `base_mirothinker.yaml` | SGLang | MiroThinker model via SGLang |
| `base_openai.yaml` | OpenAI | GPT models via OpenAI API |
| `base_kimi_k25.yaml` | OpenAI-Compatible | Kimi K2.5 model |

## Quick Setup

1. Set relevant environment variables for your chosen provider
2. Update your YAML config file with the appropriate client and base config
3. Run:
   ```bash
   bash scripts/test_single_task.sh \
     --config config/your_config.yaml \
     --task-question "Your task here"
   ```

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
