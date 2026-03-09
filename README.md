<div align="center">
  <img src="docs/mkdocs/docs/assets/miromind_logo.png" width="45%" alt="MiroMind" />

  <h3>Performance-First Agent Framework That Makes Any Model Better</h3>

[![DEMO](https://img.shields.io/badge/Demo-FFB300?style=for-the-badge&logo=airplayvideo&logoColor=white)](https://dr.miromind.ai/)
[![MODELS](https://img.shields.io/badge/Models-5EDDD2?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/miromind-ai)
[![DOCS](https://img.shields.io/badge/Docs-8CA1AF?style=for-the-badge&logo=readthedocs&logoColor=white)](https://miromindai.github.io/miroflow/)
[![WEBSITE](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://miromind.ai)
[![DISCORD](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/GPqEnkzQZd)
[![RedNote](https://img.shields.io/badge/RedNote-FF2442?style=for-the-badge&logo=revoltdotchat&logoColor=white)](https://www.xiaohongshu.com/user/profile/663098830000000003033edc)

</div>

<div align="center">
<strong>MiroFlow</strong> is the open-source agent framework that maximizes any model's agent performance — and proves it across 9+ benchmarks with reproducible results.<br>
Plug in GPT-5, Claude, <a href="https://github.com/MiroMindAI/mirothinker">MiroThinker</a>, Kimi, DeepSeek, or any OpenAI-compatible model. Same tools. Same environment. Better results.
</div>

<br>

<div align="center">
  <img src="docs/mkdocs/docs/assets/futurex_results.jpg" width="100%" alt="FutureX Benchmark Results" />
</div>

---

## 📰 News

- **[2026-03]**: **MiroFlow 1.7 + MiroThinker 1.5**: Major release with Web Application interface (FastAPI + React), comprehensive verifier system for benchmark evaluation, and expanded LLM support including Kimi K2.5 and GPT-5.

<details>
<summary><strong>Previous Updates</strong></summary>

- **[2025-09-15]**: **MiroFlow v0.3**: Enhanced codebase architecture and significantly improved benchmark performance, boosting GPT-5's prediction accuracy for future events by 11%. MiroFlow now ranks #1 in the future prediction benchmark. See [FutureX](https://futurex-ai.github.io/).
- **[2025-08-27]**: **MiroFlow v0.2**: Achieves state-of-the-art performance across [multiple agentic benchmarks](https://miromind.ai), including HLE (27.2%), HLE-Text-Only (29.5%), BrowserComp-EN (33.2%), BrowserComp-ZH (47.1%), and xBench-DeepSearch (72.0%).
- **[2025-08-26]**: Released GAIA Validation Trace (73.94% pass@1) and [Gradio Demo](https://github.com/MiroMindAI/MiroThinker/tree/main/apps/gradio-demo) for local deployment.
- **[2025-08-08]**: **MiroFlow v0.1**: Complete open-source release of the research agent framework.

</details>

---

## Architecture

<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_architecture_v1.7.png" width="100%" alt="MiroFlow Architecture" />
</div>

---

## Why MiroFlow

### Make Any Model Better
- **Model-Agnostic Performance**: Plug in any LLM — GPT-5, Claude, MiroThinker, Kimi K2.5, DeepSeek — and get better agent performance through smart rollback, iterative reasoning, and optimized tool orchestration.
- **#1 Across 9+ Benchmarks**: Reproducible state-of-the-art on FutureX, GAIA, HLE, xBench-DeepSearch, BrowseComp, and more.
- **One-Line Model Switching**: Change `provider_class` and `model_name` in YAML. Same tools, same prompts, same environment.

### Prove It
- **Standardized Evaluation**: Fair model comparison with identical infrastructure. The framework is the constant; the model is the variable.
- **Automated Multi-Run Evaluation**: Parallel runs with statistical aggregation (mean, std dev, min/max). Every result reproducible from config to score.

### Build With It
- **Skill System**: Define agent skills via `SKILL.md` — no code changes needed.
- **Agent Graph**: Compose multi-agent workflows with hierarchical graphs.
- **Web Application**: FastAPI + React interface out of the box.
- **Plugin Architecture**: `@register` decorator — extend without touching core code.
- **Zero-Code Prompts**: YAML + Jinja2 templates.
- **Cost-Effective**: Single RTX 4090 with open-source [MiroThinker](https://github.com/MiroMindAI/mirothinker).

---

## Any Model, Better Results

### Cross-Model Performance (MiroFlow Framework)

| Benchmark | MiroThinker 1.5 | Claude Sonnet 4.5 | Kimi K2.5 |
|-----------|-----------------|-------------------|-----------|
| GAIA Validation (165) | — | — | — |
| GAIA Text-Only (103) | 81.3% | — | — |
| HLE | — | — | — |
| HLE Text-Only | — | — | — |
| BrowseComp-EN | — | — | — |
| BrowseComp-ZH | 68.7% | — | — |
| xBench-DeepSearch | — | — | — |
| FutureX | **#1** | — | — |

> Each benchmark may use different tool combinations and prompts to maximize performance. See the full [Model Comparison](https://miromindai.github.io/miroflow/model_comparison/) for per-benchmark configs and reproduction scripts.

### Featured Results: [MiroThinker 1.5](https://github.com/MiroMindAI/mirothinker)

<div align="center">
  <img width="100%" alt="MiroThinker Performance" src="docs/mkdocs/docs/assets/mirothinker.png" />
</div>

<div align="center">
  <img width="100%" alt="BrowseComp MiroThinker Performance" src="docs/mkdocs/docs/assets/bc-mirothinker.png" />
</div>

Follow our detailed guides to reproduce any result in our [Benchmarks Documentation](https://miromindai.github.io/miroflow/evaluation_overview/).

---

## Quick Start

```bash
# 1. Clone and setup
git clone https://github.com/MiroMindAI/miroflow && cd miroflow
uv sync

# 2. Configure API keys (only OPENAI_API_KEY is required for this example)
cp .env.template .env
# Edit .env and set OPENAI_API_KEY (used by GPT-5 in the default quickstart config)

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

See [full documentation](https://miromindai.github.io/miroflow/quickstart/) for web app setup, more examples, and configuration options.

---

## References

If you find our work helpful, please consider citing:

**MiroThinker** (Model & Method)
```bibtex
@article{miromind2025mirothinker,
  title={MiroThinker: Pushing the Performance Boundaries of Open-Source Research Agents via Model, Context, and Interactive Scaling},
  author={MiroMind Team and Bai, Song and Bing, Lidong and Chen, Carson and Chen, Guanzheng and Chen, Yuntao and Chen, Zhe and Chen, Ziyi and Dong, Xuan and others},
  journal={arXiv preprint arXiv:2511.11793},
  year={2025}
}
```

**MiroFlow** (Framework)
```bibtex
@article{miromind2026miroflow,
  title={MiroFlow: Towards High-Performance and Robust Open-Source Agent Framework for General Deep Research Tasks},
  author={Su, Shiqian and Xing, Sen and Dong, Xuan and Zhong, Muyan and Wang, Bin and Zhu, Xizhou and Chen, Yuntao and Wang, Wenhai and Deng, Yue and Zhu, Pengxiang and others},
  journal={arXiv preprint arXiv:2602.22808},
  year={2026}
}
```

---

<div align="center">

<a href="https://github.com/MiroMindAI/miroflow/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MiroMindAI/miroflow" />
</a>

**Contributing**: [Issues](https://github.com/MiroMindAI/miroflow/issues) · [Pull Requests](https://github.com/MiroMindAI/miroflow/pulls) · [Discord](https://discord.com/invite/GPqEnkzQZd)

**License**: Apache 2.0

</div>
