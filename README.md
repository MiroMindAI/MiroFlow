<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_logo.png" width="45%" alt="MiroFlow" />
</div>

<br> 


<div align="center">

[![DEMO](https://img.shields.io/badge/Demo-FFB300?style=for-the-badge&logo=airplayvideo&logoColor=white)](https://dr.miromind.ai/)
[![MODELS](https://img.shields.io/badge/Models-5EDDD2?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/collections/miromind-ai/mirothinker-v02-68af084a18035f57b17cd902)
[![DATA](https://img.shields.io/badge/Data-0040A1?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)
[![BLOG](https://img.shields.io/badge/Blog-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://miromind.ai/blog/miroflow)

[![GITHUB](https://img.shields.io/badge/Github-24292F?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MiroMindAI)
[![DISCORD](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/GPqEnkzQZd)
[![RedNote](https://img.shields.io/badge/RedNote-FF2442?style=for-the-badge&logo=revoltdotchat&logoColor=white)](https://www.xiaohongshu.com/user/profile/5e353bd80000000001000239)

</div>

<div align="center">

## 📚 **[READ THE DOCUMENTATION](https://miromindai.github.io/MiroFlow/)**

### 🚀 [Try Demo](https://dr.miromind.ai/) 

</div>

---

**MiroFlow** is an open-source research agent framework that achieves state-of-the-art performance on representative benchmarks (FutureX, GAIA, HLE, xBench-DeepSearch, BrowserComp). It powers [MiroThinker](https://github.com/MiroMindAI/mirothinker), our open-source agent foundation model with native tool-assisted reasoning.

## 📰 News

- **[2026-03]**: 🎉 **MiroFlow 1.6 + MiroThinker 1.6**: Major release with Web Application interface (FastAPI + React), comprehensive verifier system for benchmark evaluation, and expanded LLM support including Kimi K2.5 and GPT-5.

<details>
<summary><strong>Previous Updates</strong></summary>

- **[2025-09-15]**: 🎉🎉 **MiroFlow v0.3**: Enhanced codebase architecture and significantly improved benchmark performance, boosting GPT-5's prediction accuracy for future events by 11%. MiroFlow now ranks #1 in the future prediction benchmark. See [FutureX](https://futurex-ai.github.io/).
- **[2025-08-27]**: **MiroFlow v0.2**: Achieves state-of-the-art performance across [multiple agentic benchmarks](https://miromind.ai/blog/miroflow), including HLE (27.2%), HLE-Text-Only (29.5%), BrowserComp-EN (33.2%), BrowserComp-ZH (47.1%), and xBench-DeepSearch (72.0%).
- **[2025-08-26]**: Released [GAIA Validation Trace](docs/public_trace.md) (73.94% pass@1) and [Gradio Demo](https://github.com/MiroMindAI/MiroThinker/tree/main/apps/gradio-demo) for local deployment.
- **[2025-08-08]**: **MiroFlow v0.1**: Complete open-source release of the research agent framework.

</details>

---

## 📋 Table of Contents

- 🚀 [Get Started](#-get-started-in-under-5-minutes)
- 🏗️ [Architecture](#️-architecture)
- 🌟 [Highlights](#-highlights)
- 🔧 [Models & Tools](#-supported-models--tools)
- 📈 [Benchmarks](#-performance-on-benchmarks)
- ❓ [FAQ](#-faq)
- 📖 [References](#-references)

---

## 🚀 Get Started in Under 5 Minutes

### 📋 Prerequisites

- **Python**: 3.12 or higher
- **Package Manager**: [`uv`](https://docs.astral.sh/uv/)
- **Operating System**: Linux, macOS

### ⚡ Quick Setup

**Example**: Intelligent document analysis with file processing capabilities.

```bash
# 1. Clone and setup
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. Configure API key
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Run your first agent
uv run main.py trace --config_file_name=agent_quickstart_reading --task="What is the first country listed in the XLSX file that have names starting with Co?" --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

🎉 **Expected Output:** Your agent should return **\boxed{Congo Democratic Republic}** 😊

> **💡 Tip:** If you encounter issues, check that your API key is correctly set in the `.env` file and that all dependencies are installed.

### 🌐 Web Application

MiroFlow provides a web interface powered by FastAPI and React for interactive agent tasks.

```bash
# Start the web server (auto-builds frontend on first run)
bash scripts/start_web.sh
```

Access the web interface at `http://localhost:8000` and API documentation at `http://localhost:8000/docs`.

---

## 🏗️ Architecture

<div align="center">
<img src="docs/mkdocs/docs/assets/miroflow_architecture.png" width="100%" alt="MiroFlow Architecture">
</div>

<details>
<summary><strong>📹 Demo: Research Assistant</strong></summary>
<br>
<table align="center" style="border: 1px solid #ccc; border-radius: 8px; padding: 12px; background-color: #f9f9f9; width: 60%;">
  <tr>
    <td style="text-align: center; padding: 10px;">
      <span style="font-size: 0.9em; color: #555;">Read CVPR 2025 Best Paper and Provide Research Advice</span>
      <br>
      <video src="https://github.com/user-attachments/assets/99ed3172-6e9a-467a-9ccb-be45957fe2e4"
             controls muted preload="metadata"
             width="50%" height="50%"
      </video>
    </td>
  </tr>
</table>
</details>

---

## 🌟 Highlights

- **Reproducible State-of-the-Art Performance**: #1 ranking across [multiple representative agentic benchmarks](https://miromindai.github.io/MiroFlow/evaluation_overview/), including FutureX, GAIA, HLE, xBench-DeepSearch, and BrowserComp benchmarks)
- **High Concurrency & Reliability**: Built with robust concurrency management and fault-tolerant design, MiroFlow efficiently handles rate-limited APIs and unstable networks, ensuring seamless trajectory collection and reliable execution of complex tasks.
- **Cost-Effective Deployment**: Powered by the open-source MiroThinker model, MiroFlow can run a  research agent service on a single RTX 4090. The entire stack relies on free, open-source tools, making it simple to deploy, scale, and reproduce. See [MiroThinker](https://github.com/MiroMindAI/mirothinker).

---

## 🔧 Supported Models & Tools

- **Models**: MiroThinker 1.6, GPT-4o, GPT-5, Claude, Gemini, Qwen, Kimi K2.5, etc.
- **Tools**: [Audio Transcription](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/audio_mcp_server.py), [Python](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/python_mcp_server.py), [File Reading](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/reading_mcp_server.py), [Reasoning](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/reasoning_mcp_server.py), [Google Search](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/searching_mcp_server.py), [VQA](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/vision_mcp_server.py), [Web Scraping](https://github.com/MiroMindAI/MiroFlow/blob/main/src/tool/mcp_servers/jina_scrape_llm_summary_mcp_server.py), E2B, etc.


---

## 📈 Performance on Benchmarks

We achieved the #1 ranking on the FutureX Benchmark Leaderboard as of September 10, 2025, boosting GPT-5's prediction accuracy for future events by 11%.

<div align="center">
  <img width="100%" alt="image" src="docs/mkdocs/docs/assets/futurex-09-12.png" />
</div>

We benchmark MiroFlow on a series of benchmarks, including **GAIA**, **HLE**, **BrowseComp**, and **xBench-DeepSearch**, and achieved SOTA results.

<img width="100%" alt="image" src="docs/mkdocs/docs/assets/benchmark_results.png" />

| Model/Framework | GAIA Val | HLE | HLE-Text | BrowserComp-EN | BrowserComp-ZH | xBench-DeepSearch |
|----------------|----------|-----|----------|----------------|----------------|-------------------|
| **MiroFlow** | **82.4%** | **27.2%** | 29.5% | 33.2% | **47.1%** | **72.0%** |
| OpenAI Deep Research | 67.4% | 26.6% | - | **51.5%** | 42.9% | - |
| Gemini Deep Research | - | 26.9% | - | - | - | 50+% |
| Kimi Researcher | - | - | 26.9% | - | - | 69.0% |
| WebSailor-72B | 55.4% | - | - | - | 30.1% | 55.0% |
| Manus | 73.3% | - | - | - | - | - |
| DeepSeek v3.1 | - | - | **29.8%** | - | - | 71.2% |

Follow our detailed guides to reproduce benchmark results in our [Benchmarks Documentation](https://miromindai.github.io/MiroFlow/evaluation_overview/)

---

## ❓ FAQ

<details>
<summary><strong>What API keys do I need?</strong></summary>
<br>
You only need an OpenRouter API key to get started. OpenRouter provides access to multiple language models through a single API.
</details>

<details>
<summary><strong>Can I use other language models besides OpenRouter?</strong></summary>
<br>
Yes, MiroFlow supports various language models. Check our documentation for configuration details.
</details>

<details>
<summary><strong>How do I reproduce the benchmark results?</strong></summary>
<br>
Follow our detailed <a href="https://miromindai.github.io/MiroFlow/evaluation_overview/">Benchmarks Documentation</a> for step-by-step reproduction guides.
</details>

<details>
<summary><strong>Is there commercial support available?</strong></summary>
<br>
For commercial inquiries and enterprise support, please contact us through our <a href="https://miromind.ai/">website</a>.
</details>

---

## 📖 References

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
@misc{2026miroflow,
  title={MiroFlow: A High-Performance Open-Source Research Agent Framework},
  author={MiroMind AI Team},
  howpublished={\url{https://github.com/MiroMindAI/MiroFlow}},
  year={2026}
}
```

---

<div align="center">

<a href="https://github.com/MiroMindAI/MiroFlow/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MiroMindAI/MiroFlow" />
</a>

**Contributing**: [Issues](https://github.com/MiroMindAI/MiroFlow/issues) · [Pull Requests](https://github.com/MiroMindAI/MiroFlow/pulls) · [Discord](https://discord.com/invite/GPqEnkzQZd)

**License**: Apache 2.0

</div>

