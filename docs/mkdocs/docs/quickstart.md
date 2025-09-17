
# 🚀 Get Started in Under 5 Minutes

Clone the repository, configure your API key, and run your first intelligent agent. You'll just need one `OPENROUTER_API_KEY`.

---

## 📋 Prerequisites

!!! info "System Requirements"
    - **Python**: 3.12 or higher
    - **Package Manager**: `uv`, [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
    - **Operating System**: Linux, macOS

---

## ⚡ Quick Setup

### Example 1: Intelligent document analysis with file processing capabilities

!!! example "File Processing Demo"
    This example demonstrates MiroFlow's document analysis capabilities.

```bash title="Setup Commands"
# 1. Clone and setup
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. Configure API key
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY

# 3. Run your first agent
uv run main.py trace --config_file_name=agent_quickstart_1 --task="What is the first country listed in the XLSX file that have names starting with Co?" --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

!!! success "Expected Output"
    🎉 **Expected Output:** Your agent should return **\boxed{Congo Democratic Republic}** 😊

!!! tip "Troubleshooting"
    **💡 Tip:** If you encounter issues, check that your API key is correctly set in the `.env` file and that all dependencies are installed.

!!! note "Coming Soon"
    **Coming Soon:** We will add a video demo for this example

---

### Example 2: Web research and multi-agent orchestration

!!! warning "Work in Progress"
    The example is not complete yet, to be completed

```bash title="Web Research Command"
uv run main.py trace --config_file_name=agent_quickstart_2 --task="What is the Nasdaq Composite Index at today?"
```

!!! note "Coming Soon"
    **Coming Soon:** Web research and multi-agent orchestration example

---

!!! info "Documentation Info"
    **Last Updated:** Sep 2025 · **Doc Contributor:** Team @ MiroMind AI


