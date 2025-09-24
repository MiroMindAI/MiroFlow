# Reasoning Tools (`reasoning_mcp_server.py`)

The Reasoning MCP Server provides a **pure text-based reasoning engine**. It supports logical analysis, problem solving, and planning, using LLM backends (OpenAI or Anthropic) with retry and exponential backoff for robustness.

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Pure Text Reasoning**: Logical analysis and problem solving using advanced LLM backends
    - **Step-by-Step Analysis**: Structured reasoning with detailed explanations
    - **Multi-Backend Support**: OpenAI or Anthropic models with automatic fallback

---

## Environment Variables

!!! warning "Configuration Location"
    The `reasoning_mcp_server.py` reads environment variables that are passed through the `tool-reasoning.yaml` configuration file, not directly from `.env` file.

**OpenAI Configuration:**

- `OPENAI_API_KEY`: Required API key for OpenAI services
- `OPENAI_BASE_URL`: Default = `https://api.openai.com/v1`
- `OPENAI_MODEL_NAME`: Default = `o3`

**Anthropic Configuration:**

- `ANTHROPIC_API_KEY`: Required API key for Anthropic services
- `ANTHROPIC_BASE_URL`: Default = `https://api.anthropic.com`
- `ANTHROPIC_MODEL_NAME`: Default = `claude-3-7-sonnet-20250219`

---

## Function Reference

The following function is provided by the `reasoning_mcp_server.py` MCP tool and can be called by agents:

### `reasoning(question: str)`

Perform step-by-step reasoning, analysis, and planning over a **text-only input**. This tool is specialized for **complex thinking tasks**.

!!! note "Text-Only Processing"
    This tool processes only the provided text input and will not fetch external data or context. Ensure all necessary information is included in the question.

**Parameters:**

- `question`: A detailed, complex question or problem statement that includes all necessary information

**Returns:**

- `str`: A structured, step-by-step reasoned answer

**Features:**

- Runs on OpenAI or Anthropic models, depending on available API keys
- Exponential backoff retry logic (up to 5 attempts)
- For Anthropic, uses **Thinking mode** with token budget (21k max, 19k thinking)
- Ensures non-empty responses with fallback error reporting
- Automatic backend selection based on available API keys

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI