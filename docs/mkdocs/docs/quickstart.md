# 🚀 Get Started in Under 5 Minutes

Clone the repository, configure your API keys, and run your first intelligent agent. MiroFlow provides multiple pre-configured agents for different use cases.

---

## 📋 Prerequisites

!!! info "System Requirements"
    - **Python**: 3.12 or higher
    - **Package Manager**: `uv`, [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
    - **Operating System**: Linux, macOS

---

## 🎯 Example 1: Document Analysis

!!! example "File Processing Demo"
    Analyze structured data files (Excel, CSV, PDF, etc.) with intelligent document processing.
    
    **Required:** [OPENROUTER_API_KEY](https://openrouter.ai/): to access Claude 3.7 Sonnet

```bash title="Setup and Run Document Analysis"
# 1. Clone and setup
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. Configure API key (REQUIRED for LLM access)
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY
# This key is necessary to access Claude 3.7 Sonnet for document analysis

# 3. Run document analysis
uv run main.py trace --config_file_name=agent_quickstart_reading --task="What is the first country listed in the XLSX file that have names starting with Co?" --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

**What this does:**

- Uses the `tool-reading` capability to process Excel files
- Leverages Claude 3.7 Sonnet (via OpenRouter API) for intelligent analysis
- Finds countries starting with "Co" and returns the first one

!!! success "Expected Output"
    🎉 **Expected Output:** Your agent should return **\boxed{Congo Democratic Republic}**

---

## 🎯 Example 2: Web Search Analysis

!!! example "Real-time Web Research"
    Search the web for current information and get intelligent analysis of the results.

    **Required:** [OPENROUTER_API_KEY](https://openrouter.ai/) and [SERPER_API_KEY](https://serper.dev/)

```bash title="Setup and Run Web Search"
# 1. Clone and setup (if not done already)
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. Configure API keys (if not done already)
cp .env.template .env
# Edit .env and add your OPENROUTER_API_KEY and SERPER_API_KEY
# These keys are necessary to access Claude 3.7 Sonnet and web search capabilities

# 3. Run web search analysis
uv run main.py trace --config_file_name=agent_quickstart_search --task="What is the current NASDAQ index price and what are the main factors affecting it today?"
```

**What this does:**

- Uses the `tool-searching-serper` capability to search the web
- Leverages Claude 3.7 Sonnet (via OpenRouter API) for intelligent analysis
- Searches for current NASDAQ index information and market factors
- Provides real-time financial data analysis

!!! success "Expected Output"
    🎉 **Expected Output:** Current NASDAQ index price with analysis of key market factors affecting it

---

## 🔧 Configuration Options

### Available Agent Configurations

| Agent | Tools | Use Case |
|-------|-------|----------|
| `agent_quickstart_reading` | Document reading | File analysis, data extraction, document summarization |
| `agent_quickstart_search` | Web search | Real-time information, market data, current events |

### Customizing Tasks

You can customize any task by modifying the `--task` parameter:

```bash
# Analyze different files
uv run main.py trace --config_file_name=agent_quickstart_reading \
  --task="Summarize the main findings in this document" \
  --task_file_name="path/to/your/document.pdf"

# Search for different information
uv run main.py trace --config_file_name=agent_quickstart_search \
  --task="What are the latest developments in AI technology?"
```

---

## 🐛 Troubleshooting

### Common Issues

!!! warning "API Key Issues"
    **Problem:** Agent fails to start or returns errors
    **Solution:** Ensure your API keys are correctly set in the `.env` file:
    ```bash
    OPENROUTER_API_KEY=your_key_here
    SERPER_API_KEY=your_key_here  # For web search examples
    ```


!!! warning "Tool Execution Errors"
    **Problem:** Tools fail to execute
    **Solution:** Check that all dependencies are installed:
    ```bash
    uv sync  # Reinstall dependencies
    ```

### Getting Help

- Check the [FAQ section](faqs.md) for common questions
- Review the [YAML Configuration Guide](yaml_config.md) for advanced setup
- Explore [Tool Documentation](tool_overview.md) for available capabilities

---

## 🚀 Next Steps

Once you've tried the examples above, explore more advanced features:

1. **Custom Agent Configuration**: Create your own agent setups
   ```bash
   # Copy and modify existing configs
   cp config/agent_quickstart_reading.yaml config/my_custom_agent.yaml
   ```

2. **Tool Development**: Add custom tools for your specific needs
   - See [Contributing Tools](contribute_tools.md) guide

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI