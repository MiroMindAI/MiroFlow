<div align="center" markdown="1">
  ![MiroMind Logo](assets/miromind_logo.png){ width="45%" }
</div>

<div align="center" markdown="1">
**Performance-first agent framework that makes any model better — and proves it across 9+ benchmarks.**
</div>

---

## Architecture

<div align="center" markdown="1">
  ![MiroFlow Architecture](assets/miroflow_architecture_v1.7.png){ width="100%" }
</div>

---

## Why MiroFlow

<div class="grid cards" markdown>

!!! tip "Make Any Model Better"
    Plug in any LLM — GPT-5, Claude, MiroThinker, Kimi K2.5, DeepSeek — and get better agent performance through smart rollback, iterative reasoning, and optimized tool orchestration. Change `provider_class` and `model_name` in YAML — everything else stays the same. [Learn more](why_miroflow.md)

!!! tip "Prove It With Reproducible Benchmarks"
    State-of-the-art results across 9+ benchmarks (GAIA, HLE, BrowseComp, xBench-DeepSearch, FutureX, and more). Every result is reproducible from a config file and a shell script, with automated multi-run statistical aggregation.

!!! tip "Fair Model Comparison"
    Same tools, same prompts, same infrastructure. The only variable is the model. See how different LLMs perform head-to-head on the [Model Comparison Leaderboard](model_comparison.md).

</div>

---

## What's New in v1.7

<div class="grid cards" markdown>

!!! example "Skill System"
    Define new agent skills with simple `SKILL.md` files — no code changes needed. Skills are auto-discovered from the filesystem, support sandboxed execution, and can be whitelisted for production safety. See [Core Concepts](core_concepts.md#skill-system) for details.

!!! example "Agent Graph Orchestration"
    Compose multi-agent workflows using `SequentialAgent` and agent graph configs. Agents pass context to each other via `AgentContext`, enabling modular task decomposition and flexible pipeline design. See [Core Concepts](core_concepts.md#agent-graph--multi-agent-composition) for details.

!!! example "Web Application"
    Out-of-the-box **FastAPI + React** web interface with session management, task execution monitoring, and file uploads. Get started with `bash scripts/start_web.sh`. See [Quick Start](quickstart.md#example-2-web-demo-with-mirothinker) for setup.

!!! example "Smart Rollback & Retry"
    Automatic detection and rollback of LLM output errors — format issues, truncation, refusals, and duplicate tool calls are all handled gracefully, significantly improving agent robustness.

!!! example "Plugin Architecture"
    Unified component registry with `@register` decorator for agents, IO processors, and LLM clients. Extend MiroFlow without touching core code — just register your component and reference it in config.

!!! example "Zero-Code Prompt Management"
    YAML + Jinja2 template-based prompt system. Tune agent behavior by editing config files instead of source code — no redeployment needed.

</div>

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/MiroMindAI/miroflow && cd miroflow
uv sync

# 2. Configure API keys
cp .env.template .env
# Edit .env and add your API keys (see .env.template for details)

# 3. Run your first task
bash scripts/test_single_task.sh \
  --config config/agent_quickstart.yaml \
  --task-question "What is the first country listed in the XLSX file that have names starting with Co?" \
  --file-path data/FSI-2023-DOWNLOAD.xlsx
```

Expected output: `\boxed{Congo Democratic Republic}`

**Switch models in one line** — same tools, same prompts, different LLM:

```yaml
# GPT-5
llm:
  provider_class: GPT5OpenAIClient
  model_name: gpt-5

# Claude 3.7 Sonnet
llm:
  provider_class: ClaudeAnthropicClient
  model_name: claude-3-7-sonnet-20250219

# MiroThinker (open-source, self-hosted)
llm:
  provider_class: MiroThinkerSGLangClient
  model_name: mirothinker-v1.5
```

See the [Installation Guide](quickstart.md) for web app setup, more examples, and configuration options.

---

## Any Model, Better Results

Benchmark results will be updated after comprehensive testing with v1.7. See [Evaluation Methodology](evaluation_overview.md) for detailed methodology and reproduction guides.

---

??? note "Changelog"

    **Feb 2026**

    - Added new tools: `tool-code-sandbox`, `tool-jina-scrape`, `tool-serper-search`
    - Added generic `OpenRouterClient` and `OpenAIClient` for flexible LLM access
    - Added FRAMES-Test benchmark evaluation support
    - Refactored tool system: separated Jina scraping and Serper search into standalone tools
    - Inlined eval prompts into verifiers to fix broken LLM judge

    **Oct 2025**

    - Added BrowseComp-ZH, HLE, HLE-Text, BrowseComp-EN, FinSearchComp, xBench-DS benchmarks
    - Added DeepSeek V3.1, GPT-5 integration
    - Added WebWalkerQA dataset evaluation
    - Added MiroAPI integration
    - Improved tool logs and per-task log storage
