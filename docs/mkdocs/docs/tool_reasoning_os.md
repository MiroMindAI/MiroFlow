# Reasoning Tools - Open Source (`reasoning_mcp_server_os.py`)

The Reasoning MCP Server (Open Source) provides a **pure text-based reasoning engine** using open-source models. It supports logical analysis, problem solving, and planning, with robust retry mechanisms and exponential backoff for reliability.

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Pure Text Reasoning**: Logical analysis and problem solving using open-source LLM backends
    - **Step-by-Step Analysis**: Structured reasoning with detailed explanations
    - **Open-Source Model Support**: Qwen3-235B-A22B-Thinking-2507 with automatic fallback
    - **Robust Error Handling**: Exponential backoff retry logic (up to 10 attempts)

---

## Environment Variables

!!! warning "Configuration Location"
    The `reasoning_mcp_server_os.py` reads environment variables that are passed through the `tool-reasoning-os.yaml` configuration file, not directly from `.env` file.

**Open-Source Model Configuration:**

- `REASONING_API_KEY`: Required API key for the open-source reasoning service
- `REASONING_BASE_URL`: Base URL for the reasoning service API endpoint
- `REASONING_MODEL_NAME`: Model name (default: `Qwen/Qwen3-235B-A22B-Thinking-2507`)

**Example Configuration:**
```bash
# API for Open-Source Reasoning Tool (for benchmark testing)
REASONING_MODEL_NAME="Qwen/Qwen3-235B-A22B-Thinking-2507"
REASONING_API_KEY=your_reasoning_key
REASONING_BASE_URL="https://your_reasoning_base_url/v1/chat/completions"
```

---

## Local Deployment

### Using SGLang Server

For optimal performance with the Qwen3-235B-A22B-Thinking model, deploy using SGLang:

```bash
python3 -m sglang.launch_server \
  --model-path /path/to/Qwen3-235B-A22B-Thinking-2507 \
  --tp 8 --host 0.0.0.0 --port 1234 \
  --trust-remote-code --enable-metrics \
  --log-level debug --log-level-http debug \
  --log-requests --log-requests-level 2 \
  --show-time-cost --context-length 131072
```

### Configuration for Local Deployment

When using local deployment, configure your environment variables:

```bash
REASONING_MODEL_NAME="Qwen/Qwen3-235B-A22B-Thinking-2507"
REASONING_API_KEY="dummy_key"  # Not required for local deployment
REASONING_BASE_URL="http://localhost:1234/v1/chat/completions"
```

---

## Function Reference

The following function is provided by the `reasoning_mcp_server_os.py` MCP tool and can be called by agents:

### `reasoning(question: str)`

Perform step-by-step reasoning, analysis, and planning over a **text-only input**. This tool is specialized for **complex thinking tasks** that require deep analytical reasoning.

!!! note "Text-Only Processing"
    This tool processes only the provided text input and will not fetch external data or context. Ensure all necessary information is included in the question.

**Parameters:**

- `question`: A detailed, complex question or problem statement that includes all necessary information

**Returns:**

- `str`: A structured, step-by-step reasoned answer

**Features:**

- **Open-Source Model**: Uses Qwen3-235B-A22B-Thinking-2507 for advanced reasoning
- **Robust Retry Logic**: Exponential backoff retry mechanism (up to 10 attempts)
- **Thinking Mode Support**: Automatically extracts reasoning content from thinking blocks
- **Error Handling**: Graceful fallback with informative error messages
- **Timeout Protection**: 600-second timeout for long-running reasoning tasks
- **Jittered Backoff**: Prevents thundering herd problems with randomized retry delays

**Retry Configuration:**
- Maximum retries: 10 attempts
- Initial backoff: 1.0 seconds
- Maximum backoff: 30.0 seconds
- Exponential backoff with jitter (0.8-1.2x multiplier)

---

## Usage Examples

### Complex Mathematical Problems
```python
question = """
Solve this complex optimization problem:
A company wants to minimize costs while maximizing production. 
Given constraints: 2x + 3y ≤ 100, x + y ≤ 50, x ≥ 0, y ≥ 0
Cost function: C = 5x + 8y
Production function: P = 3x + 4y
Find the optimal values of x and y.
"""
```

### Logical Puzzles
```python
question = """
Three people are in a room: Alice, Bob, and Charlie. 
- Alice says: "Bob is lying"
- Bob says: "Charlie is lying" 
- Charlie says: "Alice is lying"
If exactly one person is telling the truth, who is it?
"""
```

### Strategic Planning
```python
question = """
Design a strategy for a startup to enter a competitive market 
with limited resources. Consider market analysis, competitive 
positioning, resource allocation, and risk mitigation.
"""
```

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
