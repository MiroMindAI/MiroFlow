<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_logo.png" width="45%" alt="MiroFlow" />
</div>

<br> 

<div align="center">

[![文档](https://img.shields.io/badge/Documentation-4285F4?style=for-the-badge&logo=gitbook&logoColor=white)](https://miromindai.github.io/MiroFlow/)
[![演示](https://img.shields.io/badge/Demo-FFB300?style=for-the-badge&logo=airplayvideo&logoColor=white)](https://dr.miromind.ai/)
[![模型](https://img.shields.io/badge/Models-5EDDD2?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/collections/miromind-ai/mirothinker-v02-68af084a18035f57b17cd902)
[![数据](https://img.shields.io/badge/Data-0040A1?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)

[![博客](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://miromind.ai/)
[![GITHUB](https://img.shields.io/badge/Github-24292F?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MiroMindAI)
[![DISCORD](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/GPqEnkzQZd)
[![微信](https://img.shields.io/badge/WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white)](https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/assets/wechat.png)
[![小红书](https://img.shields.io/badge/RedNote-FF2442?style=for-the-badge&logo=revoltdotchat&logoColor=white)](https://www.xiaohongshu.com/user/profile/5e353bd80000000001000239)

</div>

<div align="center">

### 🚀 [Try our Demo!](https://dr.miromind.ai/)｜[English](README.md)｜[日本語](README_ja.md)

</div>

<div align="center">
  <img width="100%" alt="image" src="docs/mkdocs/docs/assets/futurex-09-12.png" />
</div>

---

这个仓库是MiroMind研究智能体项目的官方开源仓库。它是一个高性能、完全开源的研究智能体系统，旨在执行多步骤的互联网深度研究，用于解决复杂问题（例如：进行未来事件预测）。该项目目前包含四个核心组件：

- 🤖 MiroFlow：一个开源研究智能体框架，在代表性基准（如 FutureX、GAIA、HLE、xBench-DeepSearch、BrowserComp）上实现了可复现的最高性能（代码详见本仓库）。动手尝试一下 [[5分钟快速上手]](#-5分钟快速开始)。
- 🤔 MiroThinker：一个开源智能体基座模型，原生支持工具辅助推理。详见 [MiroThinker](https://github.com/MiroMindAI/mirothinker)。
- 📊 MiroVerse：14.7万条高质量开源训练数据，用于研究智能体训练。详见 [MiroVerse](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)。
- 🚧 MiroTrain / MiroRL：支持研究智能体模型稳定高效训练的基础设施。详见 [MiroTrain](https://github.com/MiroMindAI/MiroTrain) / [MiroRL](https://github.com/MiroMindAI/MiroRL)。

---

## 📋 目录

- 📰 [最近更新](#-最近更新)
- 🚀 [5分钟快速上手](#-5分钟快速上手)
- 🤖 [什么是 MiroFlow？](#-什么是-miroflow)
- 🌟 [核心亮点](#-核心亮点)
- ✨ [基准测试性能](#-基准测试性能)
- 🔧 [支持的模型与工具](#-支持的模型与工具)
- ❓ [常见问题](#-常见问题)
- 🤝 [贡献](#-贡献)
- 📄 [许可证](#-许可证)
- 🙏 [致谢](#-致谢)

---

## 📰 最近更新

- **[2025-09-15]**: 🎉🎉 MiroFlow v0.3：简化仓库代码架构，提升基准测试表现，使 GPT-5 的未来事件预测准确率提高 11%。MiroFlow 现已在未来预测基准中排名第一。详见 [FutureX](https://futurex-ai.github.io/)。
- **[2025-08-27]**: **MiroFlow v0.2**：在多个重要的智能体基准测试上达到最高性能，且这些性能均可通过本仓库代码复现，包括 HLE (27.2%)、HLE-Text-Only (29.5%)、BrowserComp-EN (33.2%)、BrowserComp-ZH (47.1%)、xBench-DeepSearch (72.0%)。
- **[2025-08-26]**: 发布了 [GAIA 验证轨迹](docs/public_trace.md) (73.94% pass@1) 和用于本地部署的 [Gradio 演示](https://github.com/MiroMindAI/MiroThinker/tree/main/apps/gradio-demo)。
- **[2025-08-08]**: **MiroFlow v0.1**：研究智能体框架首次完整开源发布。

---

## 🚀 5分钟快速上手

### 📋 前置条件

- **Python**: 3.12 或更高版本
- **包管理器**: [`uv`](https://docs.astral.sh/uv/)
- **操作系统**: Linux, macOS

## ⚡ 快速设置

**示例**: 带文档处理能力的智能文档分析。

```bash
# 1. 克隆并设置
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. 配置 API 密钥
cp .env.template .env
# 编辑 .env 并添加您的 OPENROUTER_API_KEY

# 3. 运行您的第一个智能体
uv run main.py trace --config_file_name=agent_quickstart_reading --task="What is the first country listed in the XLSX file that have names starting with Co?" --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

🎉 **预期输出**: 您的智能体应该返回 **\boxed{Congo Democratic Republic}** 😊

> **💡 提示**: 如果遇到问题，请检查您的 API 密钥是否在 `.env` 文件中正确设置，以及是否安装了所有依赖项。

---

## 🤖 什么是 MiroFlow？

MiroFlow 是一个高性能、模块化的研究智能体框架，能够在复杂推理任务（例如：未来事件预测）上实现最先进的效果。它支持多轮对话、高度集成的工具生态，以及分层子智能体调度，确保任务最优完成。了解更多请参见我们的 [智能体框架介绍](https://miromindai.github.io/MiroFlow/core_concepts/)。

<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_architecture.png" width="100%" alt="MiroFlow Architecture">
</div>

<table align="center" style="border: 1px solid #ccc; border-radius: 8px; padding: 12px; background-color: #f9f9f9; width: 60%;">
  <tr>
    <td style="text-align: center; padding: 10px;">
      <strong>Research Assistant Demo</strong> - 
      <span style="font-size: 0.9em; color: #555;">阅读CVPR 2025最佳论文并给出研究方向建议</span>
      <br>
      <video src="https://github.com/user-attachments/assets/99ed3172-6e9a-467a-9ccb-be45957fe2e4"
             controls muted preload="metadata"
             width="50%" height="50%"
      </video>
    </td>
  </tr>
</table>

---

## 🌟 核心亮点

- **可复现的最先进性能**：在 [多个重要的智能体基准测试](https://miromindai.github.io/MiroFlow/evaluation_overview/) 上排名第一，包括 FutureX、GAIA、HLE、xBench-DeepSearch、BrowserComp。  
- **高并发与高可靠性**：具备健壮的并发管理和容错设计，MiroFlow 能高效处理受限速 API 和不稳定网络，确保顺畅的数据收集和复杂任务的可靠执行。  
- **高性价比部署**：基于开源的 MiroThinker 模型，MiroFlow 可以在单张 RTX 4090 上运行研究智能体服务，整个栈依赖于免费开源工具，便于部署、扩展和复现，详见 [MiroThinker](https://github.com/MiroMindAI/mirothinker)。

---

## 🔧 支持的模型与工具

- **模型**: GPT, Claude, Gemini, Qwen, MiroThinker
- **工具**: [音频转录](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/audio_mcp_server.py), [Python](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/python_server.py), [文件阅读](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/reading_mcp_server.py), [推理](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/reasoning_mcp_server.py), [谷歌搜索](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/searching_mcp_server.py), [视觉问答](https://github.com/MiroMindAI/MiroFlow/blob/miroflow-v0.3/src/tool/mcp_servers/vision_mcp_server.py), E2B沙盒

---

### ✨ 基准测试性能

截至 2025 年 9 月 10 日，MiroFlow 在 **FutureX 基准排行榜** 上排名第一，使 GPT-5 的未来预测准确率提高了 **11%**。

<div align="center">
  <img width="100%" alt="image" src="docs/mkdocs/docs/assets/futurex-09-12.png" />
</div>

我们在一系列基准测试上对 MiroFlow 进行了评估，包括 **GAIA**、**HLE**、**BrowseComp** 和 **xBench-DeepSearch**，并取得了目前最好的的结果。

<img width="100%" alt="image" src="docs/mkdocs/docs/assets/benchmark_results.png" />

| 模型/框架 | GAIA Val | HLE | HLE-Text | BrowserComp-EN | BrowserComp-ZH | xBench-DeepSearch |
|-----------|----------|-----|----------|----------------|----------------|-------------------|
| **MiroFlow** | **82.4%** | **27.2%** | 29.5% | 33.2% | **47.1%** | **72.0%** |
| OpenAI Deep Research | 67.4% | 26.6% | - | **51.5%** | 42.9% | - |
| Gemini Deep Research | - | 26.9% | - | - | - | 50+% |
| Kimi Researcher | - | - | 26.9% | - | - | 69.0% |
| WebSailor-72B | 55.4% | - | - | - | 30.1% | 55.0% |
| Manus | 73.3% | - | - | - | - | - |
| DeepSeek v3.1 | - | - | **29.8%** | - | - | 71.2% |

按照我们的详细指南在我们的[基准测试文档](https://miromindai.github.io/MiroFlow/evaluation_overview/)中重现基准测试结果

---

## ❓ 常见问题

<details>
<summary><strong>我需要什么 API 密钥？</strong></summary>
<br>
您只需要一个 OpenRouter API 密钥即可开始。OpenRouter 通过单一 API 提供对多个语言模型的访问。
</details>

<details>
<summary><strong>除了 OpenRouter，我可以使用其他语言模型吗？</strong></summary>
<br>
是的，MiroFlow 支持各种语言模型。查看我们的文档了解配置详情。
</details>

<details>
<summary><strong>如何重现基准测试结果？</strong></summary>
<br>
按照我们详细的<a href="https://miromindai.github.io/MiroFlow/evaluation_overview/">基准测试文档</a>获取逐步重现指南。
</details>

<details>
<summary><strong>是否有商业支持？</strong></summary>
<br>
如需商业咨询和企业支持，请通过我们的<a href="https://miromind.ai/">官方网站</a>联系我们。
</details>

---

## 🤝 贡献

我们欢迎社区的贡献！无论您是修复错误、添加功能还是改进文档，您的帮助都是受欢迎的。

- 📋 **问题反馈**: 通过 [GitHub Issues](https://github.com/MiroMindAI/MiroFlow/issues) 报告错误或请求功能。
- 🔀 **拉取请求**: 通过拉取请求提交改进。
- 💬 **讨论**: 加入我们的 [Discord 社区](https://discord.com/invite/GPqEnkzQZd) 进行问题讨论。

## 📄 许可证

本项目在 Apache License 2.0 下许可。

## 🙏 致谢

- **基准测试贡献者** 提供了综合评估数据集。
- **开源社区** 提供了使这一切成为可能的工具和库。

我们感谢所有帮助 MiroFlow 变得更好的贡献者：

<a href="https://github.com/MiroMindAI/MiroFlow/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MiroMindAI/MiroFlow" />
</a>

加入我们的社区，帮助我们构建 AI 智能体的未来！


## 参考文献

技术报告即将发布！

```
@misc{2025mirothinker,
    title={MiroFlow: A High-Performance Open-Source Research Agent Framework},
    author={MiroMind AI Team},
    howpublished={\url{https://github.com/MiroMindAI/MiroFlow}},
    year={2025}
}
```

[![Star History Chart](https://api.star-history.com/svg?repos=MiroMindAI/MiroFlow&type=Date)](https://star-history.com/#MiroMindAI/MiroFlow&Date)
