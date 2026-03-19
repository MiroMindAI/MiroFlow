# LLM Clients Overview

MiroFlow is model-agnostic — plug in any LLM and get better agent performance through smart rollback, iterative reasoning, and optimized tool orchestration. Switch models in one line of YAML. Same tools, same prompts, same environment.

## Available Clients

| Client | Provider | Model | Benchmark Status | Environment Variables |
|--------|----------|-------|-----------------|---------------------|
| `MiroThinkerSGLangClient` | SGLang | MiroThinker series | GAIA, HLE, BrowseComp, xBench-DS, FutureX | `OAI_MIROTHINKER_API_KEY`, `OAI_MIROTHINKER_BASE_URL` |
| `ClaudeAnthropicClient` | Anthropic Direct | claude-3-7-sonnet | GAIA | `ANTHROPIC_API_KEY`, `ANTHROPIC_BASE_URL` |
| `GPT5OpenAIClient` | OpenAI | gpt-5 | — | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `GPTOpenAIClient` | OpenAI | gpt-4o, gpt-4o-mini | — | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `ClaudeOpenRouterClient` | OpenRouter | anthropic/claude-3.7-sonnet, and other [supported models](https://openrouter.ai/models) | — | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| `OpenRouterClient` | OpenRouter | Any model on OpenRouter | — | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL` |
| `OpenAIClient` | OpenAI-Compatible | Any OpenAI-compatible model | GAIA Text-Only (Kimi K2.5) | `OPENAI_API_KEY`, `OPENAI_BASE_URL` |
| `MiniMaxClient` | [MiniMax](https://platform.minimax.io) | MiniMax-M2.7, MiniMax-M2.7-highspeed | — | `MINIMAX_API_KEY`, `MINIMAX_BASE_URL` |

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
| `base_minimax.yaml` | MiniMax | MiniMax M2.7 via OpenAI-compatible API |

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

## Switch Models in One Line

Change `provider_class` and `model_name` in your YAML config — everything else stays the same:

```yaml
# GPT-5
main_agent:
  llm:
    provider_class: GPT5OpenAIClient
    model_name: gpt-5

# Claude 3.7 Sonnet
main_agent:
  llm:
    provider_class: ClaudeAnthropicClient
    model_name: claude-3-7-sonnet-20250219

# MiroThinker (open-source, self-hosted)
main_agent:
  llm:
    provider_class: MiroThinkerSGLangClient
    model_name: mirothinker-v1.5

# MiniMax M2.7
main_agent:
  llm:
    provider_class: MiniMaxClient
    model_name: MiniMax-M2.7
```

See the [Model Comparison Leaderboard](model_comparison.md) for cross-model benchmark results.

---

!!! info "Documentation Info"
    **Last Updated:** March 2026 · **Doc Contributor:** Team @ MiroMind AI
