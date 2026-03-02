# YAML Configuration Guide

MiroFlow uses a configuration system for customizing AI agents, tools, and benchmarks.

## Configuration Structure

```bash title="Configuration Directory"
config/
├── agent_*.yaml                      # Agent configurations (quickstart, web demo, etc.)
├── benchmark_*.yaml                  # Benchmark configurations
├── prompts/                          # Prompt classes (.py and .yaml)
├── llm/                              # LLM provider configurations
├── benchmark/                        # Benchmark dataset settings
└── tool/                             # Tool configurations
```

## Quick Start

**Run a Single Task**
```bash
bash scripts/test_single_task.sh \
  --config config/agent_quickstart.yaml \
  --task-question "What is the first country listed in the XLSX file that have names starting with Co?" \
  --file-path data/FSI-2023-DOWNLOAD.xlsx
```

**Run Benchmarks**
```bash
# GAIA validation with MiroThinker (8 runs)
bash scripts/benchmark/mirothinker/gaia-validation-165_mirothinker_8runs.sh

# BrowseComp English with MiroThinker (3 runs)
bash scripts/benchmark/mirothinker/browsecomp-en_mirothinker_3runs.sh

# Or run a single benchmark run directly
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_gaia-validation-165_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/gaia-validation-165/run_1"
```

---

## Core Configuration

### Basic Agent Setup

```yaml title="Basic Agent Configuration (agent_quickstart.yaml)"
defaults:
  - benchmark: example_dataset
  - override hydra/job_logging: none
  - _self_

entrypoint: main_agent

main_agent:
  name: main_agent
  type: IterativeAgentWithToolAndRollback
  max_turns: 30

  llm:
    _base_: config/llm/base_openai.yaml
    provider_class: GPT5OpenAIClient
    model_name: gpt-5
    max_tokens: 128000

  prompt: config/prompts/prompt_main_agent_benchmark.yaml

  tools:
    - config/tool/tool-reading.yaml

  input_processor:
    - ${input-message-generator}
  output_processor:
    - ${output-summary}
    - ${output-boxed-extractor}

input-message-generator:
  type: InputMessageGenerator
output-summary:
  type: SummaryGenerator
output-boxed-extractor:
  type: RegexBoxedExtractor

output_dir: logs
data_dir: "${oc.env:DATA_DIR,data}"
```

### Standard Benchmark Configuration

```yaml title="Benchmark Configuration (benchmark_gaia-validation-165_mirothinker.yaml)"
defaults:
  - benchmark: gaia-validation-165
  - override hydra/job_logging: none
  - _self_

entrypoint: main_agent
main_agent:
  name: main_agent
  type: IterativeAgentWithToolAndRollback
  max_consecutive_rollbacks: 5
  max_turns: 200

  llm:
    _base_: config/llm/base_mirothinker.yaml

  prompt: config/prompts/prompt_main_agent_benchmark.yaml

  tools:
    - config/tool/tool-code-sandbox.yaml
    - config/tool/tool-serper-search.yaml
    - config/tool/tool-jina-scrape.yaml

  tool_blacklist:
    - server: "tool-serper-search"
      tool: "sogou_search"

  input_processor:
    - ${file-content-preprocessor}
    - ${input-message-generator}
  output_processor:
    - ${output-summary}
    - ${output-boxed-extractor}
    - ${output-exceed-max-turn-summary}
```

### LLM Providers

!!! tip "Available Providers"
    - **Claude**: `ClaudeOpenRouterClient` (via OpenRouter), `ClaudeAnthropicClient` (direct)
    - **OpenAI**: `GPTOpenAIClient`, `GPT5OpenAIClient`
    - **OpenRouter (Generic)**: `OpenRouterClient` - access any model via OpenRouter
    - **OpenAI-Compatible**: `OpenAIClient` - generic client for OpenAI-compatible APIs
    - **MiroThinker**: `MiroThinkerSGLangClient`
    - **DeepSeek**: via `OpenRouterClient` or `OpenAIClient`

    See [LLM Clients Overview](llm_clients_overview.md) for details.

### Available Tools

!!! note "Tool Options"
    - **`tool-reasoning`** / **`tool-reasoning-os`**: Enhanced reasoning capabilities
    - **`tool-searching`**: Web search, Wikipedia, Archive.org, and retrieval
    - **`tool-searching-serper`** / **`tool-serper-search`**: Lightweight Google search via Serper
    - **`tool-reading`**: Document processing
    - **`tool-code-sandbox`**: Python code execution in E2B sandbox
    - **`tool-image-video`** / **`tool-image-video-os`**: Visual content analysis
    - **`tool-audio`** / **`tool-audio-os`**: Audio processing
    - **`tool-jina-scrape`**: URL scraping with LLM-powered info extraction
    - **`tool-browsing`**: Web browsing
    - **`tool-markitdown`**: Document to markdown conversion

    See [Tool Overview](tool_overview.md) for configurations.

---

## Advanced Features

### Input/Output Processors

```yaml title="Available Processors"
# Input processors
input_processor:
  - ${file-content-preprocessor}     # Pre-process file content
  - ${input-hint-generator}          # Generate hints using LLM
  - ${input-message-generator}       # Generate initial message

# Output processors
output_processor:
  - ${output-summary}                # Summarize conversation
  - ${output-boxed-extractor}        # Extract \boxed{} answers via regex
  - ${output-final-answer-extraction} # Extract final answer using LLM
  - ${output-exceed-max-turn-summary} # Summarize when max turns exceeded
```

### Benchmark Settings

```yaml title="Benchmark Configuration (config/benchmark/)"
name: "your-benchmark"
data:
  data_dir: "${data_dir}/your-data"
execution:
  max_tasks: null      # null = no limit
  max_concurrent: 3    # Parallel tasks
  pass_at_k: 1         # Attempts per task
```

### Tool Blacklist

You can disable specific tools from a tool server:

```yaml title="Tool Blacklist"
tool_blacklist:
  - server: "tool-serper-search"
    tool: "sogou_search"
  - server: "tool-code-sandbox"
    tool: "download_file_from_sandbox_to_local"
```

---

## Environment Variables

```bash title="Required .env Configuration"
# LLM Providers
OPENROUTER_API_KEY="your_key"
ANTHROPIC_API_KEY="your_key"
OPENAI_API_KEY="your_key"
OAI_MIROTHINKER_API_KEY="your_key"
OAI_MIROTHINKER_BASE_URL="your_url"

# Tools
SERPER_API_KEY="your_key"
JINA_API_KEY="your_key"
E2B_API_KEY="your_key"

# Optional
DATA_DIR="data/"
CHINESE_CONTEXT="false"
```

---

## Key Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `temperature` | LLM creativity (0.0-1.0) | 0.3 |
| `max_tokens` | Response length limit | 32000 |
| `max_turns` | Conversation turns (-1 = unlimited) | -1 |
| `max_consecutive_rollbacks` | Max consecutive rollbacks before stopping | 5 |
| `max_concurrent` | Parallel benchmark tasks | 3 |

---

## Best Practices

!!! success "Quick Tips"
    - **Start simple**: Use `agent_quickstart.yaml` as a base
    - **Tool selection**: Choose tools based on your task requirements
    - **API keys**: Always use environment variables, never hardcode
    - **Resource limits**: Set `max_concurrent` and `max_tokens` appropriately
    - **Benchmark configs**: Use the `benchmark_*_mirothinker.yaml` configs for reproducing benchmark results

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
