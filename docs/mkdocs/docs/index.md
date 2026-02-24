<div align="center" markdown="1">
  ![MiroFlow Logo](assets/miroflow_logo.png){ width="45%" }
</div>

<div align="center" markdown="1">
**Open-source research agent framework with state-of-the-art performance across representative benchmarks.**
</div>

---

## Why MiroFlow?

<div class="grid cards" markdown>

!!! success "State-of-the-Art Performance"
    **#1 ranking** across multiple agentic benchmarks including FutureX, GAIA, HLE, xBench-DeepSearch, and BrowseComp. All results are fully reproducible.

!!! abstract "High Concurrency & Reliability"
    Robust concurrency management and fault-tolerant design for handling rate-limited APIs and unstable networks at scale.

!!! tip "Cost-Effective Deployment"
    Run a full research agent on a **single RTX 4090** with the open-source [MiroThinker](https://github.com/MiroMindAI/mirothinker) model. No proprietary tools required.

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

See the [Installation Guide](quickstart.md) for web app setup, more examples, and configuration options.

---

## Benchmark Results

<div align="center" markdown="1">
  ![MiroThinker Performance](assets/mirothinker.png){ width="100%" }
</div>

<div align="center" markdown="1">
  ![BrowseComp MiroThinker Performance](assets/bc-mirothinker.png){ width="100%" }
</div>

See [Benchmarks Overview](evaluation_overview.md) for detailed results and reproduction guides.

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
