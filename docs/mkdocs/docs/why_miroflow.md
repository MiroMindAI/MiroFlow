# Why MiroFlow

## The Problem

Most agent frameworks are tightly coupled to a single model or provider. When you want to compare model performance, you face several challenges:

- **No standardized environment**: Different frameworks use different tools, prompts, and infrastructure — making cross-model comparison meaningless.
- **Non-reproducible results**: Published benchmark numbers often lack reproducible configs, making it impossible to verify claims.
- **Single-model lock-in**: Frameworks optimized for one model often perform poorly with others, forcing you to rewrite pipelines when switching providers.

MiroFlow solves all three problems.

---

## Performance-First Framework

MiroFlow maximizes any model's agent performance through architecture designed for robustness and efficiency:

### Smart Rollback & Retry

LLMs fail in predictable ways — malformed tool calls, truncated output, refusals, repetitive loops. MiroFlow detects these failures automatically and rolls back to a clean state with accumulated error feedback, giving the model context about what went wrong. This dramatically improves success rates across all models.

### Optimized Tool Orchestration

Tools are connected via the MCP protocol with unified error handling, timeout management, and retry logic. Every model gets the same high-quality tool implementations — search, code execution, file reading, web browsing, and more.

### Iterative Reasoning

The `IterativeAgentWithToolAndRollback` agent type handles multi-step reasoning with configurable turn limits, rollback thresholds, and duplicate detection. The agent keeps working until it reaches a final answer or exhausts its budget.

### Modular IO Pipeline

Composable input and output processors handle file preprocessing, hint generation, answer extraction, and summarization. The pipeline is configured in YAML and shared across all models — ensuring consistent task presentation and result extraction.

---

## Standardized Evaluation

MiroFlow provides the infrastructure for fair, reproducible model comparison:

### Same Environment for Every Model

| Component | Guarantee |
|-----------|-----------|
| **Tools** | Identical MCP tool configurations (search, code sandbox, file reading, etc.) |
| **Prompts** | Same YAML + Jinja2 templates |
| **Verifiers** | Same automated scoring per benchmark |
| **IO Pipeline** | Same input preprocessing and output extraction |
| **Rollback Logic** | Same error recovery behavior |

### 9+ Benchmarks

| Benchmark | Category | Measures |
|-----------|----------|----------|
| GAIA | General Agent | Multi-step reasoning with tool use |
| HLE | Language Understanding | Hard language and reasoning problems |
| BrowseComp (EN/ZH) | Web Search | Complex web-based fact retrieval |
| xBench-DeepSearch | Deep Search | Multi-hop information retrieval |
| FutureX | Future Prediction | Event forecasting with reasoning |
| FinSearchComp | Finance | Financial information retrieval |
| WebWalkerQA | Web Navigation | Question answering via web browsing |
| FRAMES-Test | Multi-hop QA | Complex multi-hop reasoning |

### Automated Multi-Run Evaluation

Benchmark scripts run multiple evaluation passes in parallel and aggregate results with statistical reporting:

- **Mean accuracy** across runs
- **Standard deviation** for reliability assessment
- **Min/max** for worst/best case analysis

Every result is reproducible from a config file and a shell script.

---

## One-Line Model Switching

Switch between any supported model by changing two lines in your YAML config:

```yaml
# GPT-5
main_agent:
  llm:
    provider_class: GPT5OpenAIClient
    model_name: gpt-5
```

```yaml
# Claude 3.7 Sonnet
main_agent:
  llm:
    provider_class: ClaudeAnthropicClient
    model_name: claude-3-7-sonnet-20250219
```

```yaml
# MiroThinker (open-source, self-hosted)
main_agent:
  llm:
    provider_class: MiroThinkerSGLangClient
    model_name: mirothinker-v1.5
```

```yaml
# Kimi K2.5
main_agent:
  llm:
    _base_: config/llm/base_kimi_k25.yaml
    provider_class: OpenAIClient
    model_name: kimi-k2.5
```

```yaml
# Any OpenAI-compatible API
main_agent:
  llm:
    provider_class: OpenAIClient
    model_name: your-model-name
```

Everything else — tools, prompts, rollback logic, IO pipeline — stays the same.

---

## See the Results

Visit the [Model Comparison Leaderboard](model_comparison.md) to see how different models perform on the same benchmarks with the same infrastructure.

---

!!! info "Documentation Info"
    **Last Updated:** March 2026 · **Doc Contributor:** Team @ MiroMind AI
