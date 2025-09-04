<div align="center">
  <img src="docs/figs/MiroFlow_logo.png" width="65%" alt="MiroFlow" />
</div>

<br> 

<div align="center">

[![MODELS](https://img.shields.io/badge/MiroThinker_Models-5EDDD2?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/collections/miromind-ai/mirothinker-v01-689301b6d0563321862d44a1)
[![DATA](https://img.shields.io/badge/MiroVerse_Data-0040A1?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)
[![WEBSITE](https://img.shields.io/badge/MiroMind_Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://miromind.ai/)

[![DISCORD](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/GPqEnkzQZd)
[![WeChat](https://img.shields.io/badge/WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white)](https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/assets/wechat.png)
[![RedNote](https://img.shields.io/badge/RedNote-FF2442?style=for-the-badge&logo=revoltdotchat&logoColor=white)](https://www.xiaohongshu.com/user/profile/5e353bd80000000001000239)
[![DeepWiki](https://img.shields.io/badge/DeepWiki-grey?style=for-the-badge&logo=deepwiki&logoColor=white)](https://deepwiki.com/MiroMindAI/MiroFlow)

# 🚀[Please try our Demo!](https://dr.miromind.ai/)🚀

</div>

# MiroFlow: A Leading "Open Deep Research" Project

<img src="docs/figs/logo.png" alt="MiroFlow Logo" width="150" align="right">


- [📰 News & Updates](#-news--updates)
- [📝 Introduction](#-introduction)
- [✨ Performance on Benchmarks](#-performance-on-benchmarks)
- [🚀 Getting Started](#-getting-started)
- [🌟 MiroThinker](docs/mirothinker.md)
- [📄 License & Support](#-license--support)


## 📰 News & Updates

- **2025-08-27**: 🎉 **MiroFlow v0.2** - Achieves SOTA performance across [multiple agentic benchmarks](https://miromind.ai/blog/miroflow). Highlights include **HLE 27.2%**, **HLE-Text-Only 29.5%**, **BrowserComp-EN 33.2%**, **BrowserComp-ZH 47.1%**, and **xBench-DeepSearch 72.0%**.
- **2025-08-26**: 🎉 [GAIA Validation Trace](apps/public-trace/gaia-validation) released (73.94% with pass@1) and [Gradio Demo](https://github.com/MiroMindAI/MiroThinker/tree/main/apps/gradio-demo) released for local deployment.
- **2025-08-08**: 🎉 **MiroFlow v0.1** - Framework, model, and data are now fully open-sourced!


## 📝 Introduction

**MiroFlow** is a fully open-sourced agent framework designed to reliably complete complex tool-use tasks. Our comprehensive ecosystem includes the following key components:

- 🌟 **Reproducible SOTA Performance**: MiroFlow consistently achieves 72.2% (pass@1 average@3) on the GAIA benchmark. Follow our detailed guide to reproduce our released GAIA traces and verify results.
- 🌟 **Advanced Data Collection**: Our framework features sophisticated data collection capabilities that generate high-quality, post-training agent trace data. We've open-sourced extensive datasets through [MiroVerse](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1).
- 🌟 **Open Source Models**: We provide fully open-sourced models that you can deploy locally and fine-tune for your specific needs. Explore our model collection at [MiroThinker](https://huggingface.co/collections/miromind-ai/mirothinker-v01-689301b6d0563321862d44a1).
- 🌟 **Comprehensive Training Framework**: We've open-sourced our complete SFT and DPO training recipes, available at [MiroTrain](https://github.com/MiroMindAI/MiroTrain).
- 🌟 **Reinforcement Learning Framework**: Our RL training exploration and methodologies are fully available through [MiroRL](https://github.com/MiroMindAI/MiroRL).



## ✨ Performance on Benchmarks

<div align="center">
  <img src="docs/figs/09xyHJV9dkbY2yacsv4zYTBbKM.avif" width="90%" alt="Comprehensive Benchmark Performance Comparison" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
</div>

We benchmark MiroFlow on a series of benchmarks including **GAIA**, **HLE**, **BrowseComp** and **xBench-DeepSearch**. Meantime, we are working on more benchmarks.

| Model/Framework | GAIA Val | HLE | HLE-Text | BrowserComp-EN | BrowserComp-ZH | xBench-DeepSearch |
|----------------|----------|-----|----------|----------------|----------------|-------------------|
| **MiroFlow** | **82.4%** | **27.2%** | 29.5% | 33.2% | **47.1%** | **72.0%** |
| OpenAI Deep Research | 67.4% | 26.6% | - | **51.5%** | 42.9% | - |
| Gemini Deep Research | - | 26.9% | - | - | - | 50+% |
| Kimi Researcher | - | - | 26.9% | - | - | 69.0% |
| WebSailor-72B | 55.4% | - | - | - | 30.1% | 55.0% |
| Manus | 73.3% | - | - | - | - | - |
| DeepSeek v3.1 | - | - | **29.8%** | - | - | 71.2% |



### GAIA-Validation

<img src="docs/figs/gaia_score.png" width="40%" alt="GAIA Validation Performance" align="right">

MiroFlow **achieved 81.8% pass@3, 82.4% maj. vote, 74.5% pass@1 (best@3), and 72.2% pass@1 (avg@3) on the GAIA validation set**. This represents **state-of-the-art (SOTA) performance** among open-source agent frameworks.

> [!NOTE]
> Our pass@1 scores are reported as both the average across three runs (avg@3) and the best score among those runs (best@3). For most other reported pass@1 results, it is unclear whether they represent an average or a best score across multiple trials (indicated with *). 

To prevent agents from retrieving answers directly from Hugging Face, we disabled access to it during the inference and trace collection.

*We have evaluated multiple agent frameworks on GAIA. Please note that some reported results may be overstated or lack clear definitions, and are not reproducible.*
In contrast, reproducing MiroFlow's results is straightforward with just a few required API keys.


# 🤖 MiroFlow: Modular AI Agent Framework

MiroFlow is a high-performance, modular framework for building intelligent AI agents that achieve state-of-the-art results on complex benchmarks. It features multi-turn conversation capabilities, comprehensive tool integration, and hierarchical sub-agent support for superior task completion.

<div align="center">
<img src="docs/figs/miroflow_architecture.png" width="60%" alt="MiroFlow Architecture">
</div>

More information on our agent [workflow](docs/workflow.md).


<a id="get-start"></a>
# 🚀 Getting Started

### Prerequisites
> [!TIP]
> we recommend using [`uv`](https://docs.astral.sh/uv/) with `python>= 3.12` 

### Step 1: Clone repo and prepare python environment

```bash
## clone the repo
git clone https://github.com/MiroMindAI/MiroFlow
cd MiroFlow/apps/run-agent

## prepare python environment
uv sync
```

### Step 2: Set up environment variables

#### a. Set up `MiroFlow/apps/prepare-benchmark/.env`

```bash
## copy environment variable template and prepare yours in .env file
cd MiroFlow/apps/prepare-benchmark

# Edit .env with your actual API keys
cp .env.template .env
```

Edit `.env` to configure environment variables:

```env
# For downloading datasets from Hugging Face
HF_TOKEN="<your-huggingface-token>"

# [Optional] Data loading directory, by default `../../data`
DATA_DIR="../../data" # relative to this file 
```

#### b. Set up `MiroFlow/apps/run-agent/.env`

```bash
## copy environment variable template and prepare yours in .env file
cd MiroFlow/apps/run-agent

# Edit .env with your actual API keys
cp .env.template .env
```

Edit `.env` to configure environment variables:

```env
# Using OpenRouter to provide primary agent model
OPENROUTER_API_KEY=""
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Anthropic, for vision tools
ANTHROPIC_API_KEY=""
ANTHROPIC_BASE_URL="https://api.anthropic.com"

# OpenAI, for audio tools, intent recognition, and answer extraction
OPENAI_API_KEY=""
OPENAI_BASE_URL="https://api.openai.com/v1"

# Gemini, for YouTube tasks
GEMINI_API_KEY=""

# Third party API keys
# For Google search and website scraping
SERPER_API_KEY=""
# For website scraping
JINA_API_KEY=""
# For the Linux sandbox
E2B_API_KEY=""

# [Optional] NewAPI, alternative to OpenRouter 
NEWAPI_API_KEY=""
NEWAPI_BASE_URL=""

# [Optional] for network proxy, null by default
HTTPS_PROXY=""
# [Optional] Data loading directory, by default `../../data`
DATA_DIR="../../data"
```

> [!NOTE]
> If you wish to use a different LLM as the primary agent model, you will need to provide the corresponding API keys.

### Step 3: Local E2B Sandbox Deployment
To achieve our best benchmark results, we recommend using a pre-defined sandbox template that includes the most commonly used Python and apt packages. Please see our [installation guide](docs/local_e2b.md) for detailed instructions.

If you prefer not to use a sandbox template, you can disable it by commenting out the line `template=DEFAULT_TEMPLATE_ID,` in `libs/miroflow-tool/src/miroflow/tool/mcp_servers/python_server.py` (line 145).


### Run a single task

```bash
## run a task with instruction
cd MiroFlow/apps/run-agent
uv run main.py trace --task="your task description" --task_file_name="path to related task file"
```

### Evaluate on Benchmark

Prepare datasets according to your requirements. Some datasets may need to be downloaded manually into the `/data/<benchmark>` folder, and you should also create a corresponding `standardized_data.jsonl` metafile. We will support as many datasets as possible as soon as we can.
```bash
## supported benchmarks
cd MiroFlow/apps/prepare-benchmark
uv run main.py get gaia-val
uv run main.py get browsecomp-test
uv run main.py get browsecomp-zh-test
uv run main.py get hle
```

Run evaluation using the default settings. (Not parallelized; not recommended.)
```bash
## run the code
cd MiroFlow/apps/run-agent
uv run main.py common-benchmark benchmark=gaia-validation
uv run main.py common-benchmark benchmark=browsecomp
uv run main.py common-benchmark benchmark=browsecomp-zh
uv run main.py common-benchmark benchmark=hle
```

For parallel and multi-run evaluations, and to gain better control over environment settings using Hydra, **we recommend using the provided script**:

```bash
cd MiroFlow/apps/run-agent
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_gaia-validation.sh
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_browsecomp.sh
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_browsecomp-zh.sh
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_hle.sh
```

You can easily modify and customize these scripts to suit your needs. See [Customized Configuration](#customized-configuration) for more details.

### Customized Configuration

MiroFlow leverages [Hydra](https://hydra.cc/) for powerful configuration management, allowing you to easily switch between different LLMs, agents, benchmarks, and pricing models using YAML configuration files. For detailed instructions on configuration management, see our [configuration guide](docs/hydra_config.md).



## 📄 License & Support

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details. Some components may have different licenses as specified in their respective file headers.

### 🙏 Acknowledgments

- **Benchmark Contributors** for the comprehensive evaluation datasets
- **Open Source Community** for the tools and libraries that make this possible

### 🔧 Support

- Issues: For questions or bug reports, please use [GitHub Issues](https://github.com/MiroMindAI/MiroFlow/issues).
- FAQ Documentation: See [faq.md](docs/faq.md) for additional guidelines


<div align="center">
    <img src="https://api.star-history.com/svg?repos=MiroMindAI/MiroFlow&type=Date" alt="Star History Chart" height="300">
</div>

### References

```
@misc{2025mirothinker,
    title={MiroFlow: An Open-Source Agentic Framework for Deep Research},
    author={MiroMind AI Team},
    howpublished={\url{https://github.com/MiroMindAI/MiroFlow}},
    year={2025}
}
```
