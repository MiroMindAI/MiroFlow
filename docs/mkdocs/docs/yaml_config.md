# YAML Configuration Guide

MiroFlow uses a Hydra-based configuration system for customizing AI agents, tools, and benchmarks.

## Configuration Structure

```bash title="Configuration Directory"
config/
├── agent_*.yaml                      # Agent configurations
├── agent_prompts/                    # Prompt classes
├── benchmark/                        # Benchmark settings
└── tool/                             # Tool configurations
```

## Quick Start

**Run Benchmarks**
```bash
# GAIA validation
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation \
  output_dir="logs/gaia-validation/$(date +"%Y%m%d_%H%M")"

# GAIA text-only
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation-text-only \
  output_dir="logs/gaia-validation-text-only/$(date +"%Y%m%d_%H%M")"
```

**Single Task**
```bash
uv run main.py trace \
  --config_file_name=agent_quickstart_reading \
  --task="Your task here" \
  --task_file_name="data/file.xlsx"
```

---

## Core Configuration

### Basic Agent Setup

```yaml title="Basic Agent Configuration"
defaults:
  - benchmark: gaia-validation
  - override hydra/job_logging: none
  - _self_

main_agent:
  prompt_class: MainAgentPromptBoxedAnswer
  llm:
    provider_class: "ClaudeOpenRouterClient"
    model_name: "anthropic/claude-3.7-sonnet"
    temperature: 0.3
    max_tokens: 32000
    openrouter_api_key: "${oc.env:OPENROUTER_API_KEY,???}"
  
  tool_config: []  # Tools for main agent
  max_turns: -1    # -1 = unlimited

sub_agents:
  agent-worker:
    prompt_class: SubAgentWorkerPrompt
    llm:
      provider_class: "ClaudeOpenRouterClient"
      model_name: "anthropic/claude-3.7-sonnet"
    tool_config:
      - tool-reading
      - tool-searching
    max_turns: -1

output_dir: logs/
data_dir: "${oc.env:DATA_DIR,data}"
```

### LLM Providers

!!! tip "Available Providers"
    - **Claude**: `ClaudeOpenRouterClient`, `ClaudeAnthropicClient`
    - **OpenAI**: `GPTOpenAIClient`
    - **MiroThinker**: `MiroThinkerSGLangClient`
    - **Qwen**: `QwenSGLangClient`
    - **DeepSeek**: `DeepSeekNewAPIClient` (limited support)

    See [LLM Clients Overview](llm_clients_overview.md) for details.

### Available Tools

!!! note "Tool Options"
    - **`tool-reasoning`**: Enhanced reasoning capabilities
    - **`tool-searching`**: Web search and retrieval
    - **`tool-reading`**: Document processing
    - **`tool-code`**: Python code execution
    - **`tool-image-video`**: Visual content analysis
    - **`tool-audio`**: Audio processing
    - **`tool-browsing`**: Web browsing

    See [Tool Overview](tool_overview.md) for configurations.

---

## Advanced Features

### GAIA Benchmark Configuration

```yaml title="GAIA-Optimized Setup"
main_agent:
  prompt_class: MainAgentPrompt_GAIA
  tool_config:
    - tool-reasoning
  
  input_process:
    hint_generation: true      # Use LLM for task hint generation
  output_process:
    final_answer_extraction: true  # Use LLM for answer extraction

sub_agents:
  agent-worker:
    tool_config:
      - tool-searching
      - tool-reading
      - tool-code
      - tool-image-video
      - tool-audio
```

### Benchmark Settings

```yaml title="Benchmark Configuration"
name: "your-benchmark"
data:
  data_dir: "${data_dir}/your-data"
execution:
  max_tasks: null      # null = no limit
  max_concurrent: 3    # Parallel tasks
  pass_at_k: 1         # Attempts per task
```

---

## Environment Variables

```bash title="Required .env Configuration"
# LLM Providers
OPENROUTER_API_KEY="your_key"
ANTHROPIC_API_KEY="your_key"
OPENAI_API_KEY="your_key"

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
| `max_tool_calls_per_turn` | Tool calls per turn | 10 |
| `max_concurrent` | Parallel benchmark tasks | 3 |

---

## Best Practices

!!! success "Quick Tips"
    - **Start simple**: Use `agent_quickstart_reading.yaml` as a base
    - **Tool selection**: Choose tools based on your task requirements
    - **API keys**: Always use environment variables, never hardcode
    - **Resource limits**: Set `max_concurrent` and `max_tokens` appropriately
    - **Development**: Use higher `temperature` and unlimited `max_turns` for exploration

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI