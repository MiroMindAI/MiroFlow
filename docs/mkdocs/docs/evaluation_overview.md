# Performance Benchmarks

MiroFlow achieves state-of-the-art performance across multiple agentic benchmarks, demonstrating its effectiveness in complex reasoning and tool-use tasks.

---

## MiroThinker Performance

<div align="center" markdown="1">
  ![MiroThinker Performance](assets/mirothinker.png){ width="100%" }
</div>

<div align="center" markdown="1">
  ![BrowseComp MiroThinker Performance](assets/bc-mirothinker.png){ width="100%" }
</div>

---

## Detailed Results

!!! info "Detailed Performance Comparison"
    Comprehensive comparison across multiple benchmark categories and competing frameworks.

### Reasoning & Language Understanding

| Model/Framework | GAIA Val | HLE | HLE-Text |
|----------------|----------|-----|----------|
| **MiroFlow** | **82.4%** | **27.2%** | 29.5% |
| OpenAI Deep Research | 67.4% | 26.6% | - |
| Gemini Deep Research | - | 26.9% | - |
| Kimi Researcher | - | - | 26.9% |
| WebSailor-72B | 55.4% | - | - |
| Manus | 73.3% | - | - |
| DeepSeek v3.1 | - | - | **29.8%** |

### Web Browsing & Search Tasks

| Model/Framework | BrowserComp-EN | BrowserComp-ZH | xBench-DeepSearch |
|----------------|----------------|----------------|-------------------|
| **MiroFlow** | 33.2% | **47.1%** | **72.0%** |
| OpenAI Deep Research | **51.5%** | 42.9% | - |
| Gemini Deep Research | - | - | 50+% |
| Kimi Researcher | - | - | 69.0% |
| WebSailor-72B | - | 30.1% | 55.0% |
| DeepSeek v3.1 | - | - | 71.2% |

---

## Reproduce Results

Follow the benchmark-specific guides in the sidebar to reproduce each result. Each guide includes dataset preparation, configuration, and execution steps.
