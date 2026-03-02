# Get Started in Under 5 Minutes

Clone the repository, configure your API keys, and run your first intelligent agent with any model. MiroFlow provides pre-configured agents for different use cases.

---

## Prerequisites

!!! info "System Requirements"
    - **Python**: 3.11 or higher (< 3.14)
    - **Package Manager**: `uv`, [https://docs.astral.sh/uv/](https://docs.astral.sh/uv/)
    - **Operating System**: Linux, macOS

---

## Example 1: Document Analysis

!!! example "File Processing Demo"
    Analyze structured data files (Excel, CSV, PDF, etc.) with intelligent document processing.

    **Required:** [OPENAI_API_KEY](https://platform.openai.com/): to access GPT-5

```bash title="Setup and Run Document Analysis"
# 1. Clone and setup
git clone https://github.com/MiroMindAI/miroflow && cd miroflow
uv sync

# 2. Configure API key (REQUIRED for LLM access)
cp .env.template .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run document analysis
bash scripts/test_single_task.sh \
  --config config/agent_quickstart.yaml \
  --task-question "What is the first country listed in the XLSX file that have names starting with Co?" \
  --file-path data/FSI-2023-DOWNLOAD.xlsx
```

**What this does:**

- Uses the `tool-reading` capability to process Excel files
- Leverages GPT-5 (via OpenAI API) for intelligent analysis
- Finds countries starting with "Co" and returns the first one

!!! success "Expected Output"
    **Expected Output:** Your agent should return **\boxed{Congo Democratic Republic}**

---

## Example 2: Web Demo with MiroThinker

!!! example "Interactive Web Demo"
    Run the web application with MiroThinker for interactive agent tasks including web search, code execution, and file analysis.

    **Required:** [OAI_MIROTHINKER_API_KEY](https://github.com/MiroMindAI/mirothinker), [SERPER_API_KEY](https://serper.dev/), [E2B_API_KEY](https://e2b.dev/)

```bash title="Setup and Run Web Demo"
# 1. Clone and setup (if not done already)
git clone https://github.com/MiroMindAI/miroflow && cd miroflow
uv sync

# 2. Configure API keys (if not done already)
cp .env.template .env
# Edit .env and add your OAI_MIROTHINKER_API_KEY, SERPER_API_KEY, E2B_API_KEY

# 3. Start the web application
bash scripts/start_web.sh
```

**What this does:**

- Starts a FastAPI + React web interface using `config/agent_web_demo.yaml`
- Uses MiroThinker (via SGLang) for intelligent analysis
- Provides access to tools: code sandbox, Serper search, Jina scrape, and file reading

---

## Example 3: Same Task, Different Model

!!! example "Switch LLMs in One Line"
    Run the same task with a different model by changing the LLM config. Same tools, same prompts, same environment — only the model changes.

Copy the quickstart config and change the LLM section:

```yaml title="config/agent_quickstart_claude.yaml (example)"
main_agent:
  llm:
    provider_class: ClaudeAnthropicClient
    model_name: claude-3-7-sonnet-20250219
```

```yaml title="config/agent_quickstart_mirothinker.yaml (example)"
main_agent:
  llm:
    provider_class: MiroThinkerSGLangClient
    model_name: mirothinker-v1.5
```

Then run the same task:

```bash
# With Claude
bash scripts/test_single_task.sh \
  --config config/agent_quickstart_claude.yaml \
  --task-question "What is the first country listed in the XLSX file that have names starting with Co?" \
  --file-path data/FSI-2023-DOWNLOAD.xlsx

# With MiroThinker
bash scripts/test_single_task.sh \
  --config config/agent_quickstart_mirothinker.yaml \
  --task-question "What is the first country listed in the XLSX file that have names starting with Co?" \
  --file-path data/FSI-2023-DOWNLOAD.xlsx
```

See [Model Comparison](model_comparison.md) for benchmark results across models.

---

## Configuration Options

### Available Agent Configurations

| Config File | LLM | Tools | Use Case |
|-------------|-----|-------|----------|
| `agent_quickstart.yaml` | GPT-5 | Document reading | File analysis, data extraction |
| `agent_web_demo.yaml` | MiroThinker | Code sandbox, Serper search, Jina scrape, reading | Interactive web demo |
| `agent_single-test.yaml` | GPT-5 | Configurable | Single task testing |

### Customizing Tasks

You can customize any task using the `test_single_task.sh` script:

```bash
# Analyze different files
bash scripts/test_single_task.sh \
  --config config/agent_quickstart.yaml \
  --task-question "Summarize the main findings in this document" \
  --file-path path/to/your/document.pdf

# Or run directly with Python
uv run python scripts/run_single_task.py \
  --config-path config/agent_quickstart.yaml \
  --task-question "What is the first country listed in the XLSX file that have names starting with Co?" \
  --file-path data/FSI-2023-DOWNLOAD.xlsx
```

---

## Troubleshooting

### Common Issues

!!! warning "API Key Issues"
    **Problem:** Agent fails to start or returns errors
    **Solution:** Ensure your API keys are correctly set in the `.env` file:
    ```bash
    OPENAI_API_KEY=your_key_here          # For GPT-5
    SERPER_API_KEY=your_key_here           # For web search
    E2B_API_KEY=your_key_here              # For code sandbox
    OAI_MIROTHINKER_API_KEY=your_key_here  # For MiroThinker
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

## Next Steps

Once you've tried the examples above, explore more advanced features:

1. **Run Benchmarks**: Evaluate agent performance on standard benchmarks
   - See [Benchmarks Overview](evaluation_overview.md)

2. **Tool Development**: Add custom tools for your specific needs
   - See [Contributing Tools](contribute_tools.md) guide

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
