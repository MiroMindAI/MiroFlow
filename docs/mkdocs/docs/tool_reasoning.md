# Reasoning Tools (`reasoning_mcp_server.py`)

The Reasoning MCP Server provides a **pure text-based reasoning engine**. It supports logical analysis, problem solving, and planning, using LLM backends (OpenAI or Anthropic) with retry and exponential backoff for robustness.

## Environment Variables
!!! warning "Where to Modify"
    The `reasoning_mcp_server.py` reads environment variables that are passed through the `tool-reasoning.yaml` configuration file, not directly from `.env` file.
- OpenAI Configuration:
    - `OPENAI_API_KEY`
    - `OPENAI_BASE_URL` : default = `https://api.openai.com/v1`
    - `OPENAI_MODEL_NAME` : default = `o3`

- Anthropic Configuration:
    - `ANTHROPIC_API_KEY`
    - `ANTHROPIC_BASE_URL` : default = `https://api.anthropic.com`
    - `ANTHROPIC_MODEL_NAME` : default = `claude-3-7-sonnet-20250219`

---

## `reasoning(question: str)`
Perform step-by-step reasoning, analysis, and planning over a **text-only input**. This tool is specialized for **complex thinking tasks**.

**Parameters**

- `question`:  A detailed, complex question or problem statement that includes all necessary information. The tool will not fetch external data or context.

**Returns**

- `str`: A structured, step-by-step reasoned answer.

**Features**

- Runs on OpenAI or Anthropic models, depending on available API keys.
- Exponential backoff retry logic (up to 5 attempts).
- For Anthropic, uses **Thinking mode** with token budget (21k max, 19k thinking).
- Ensures non-empty responses with fallback error reporting.

---

**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI