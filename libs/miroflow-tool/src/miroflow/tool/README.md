# MCP Tools Framework

This document explains how Model Context Protocol (MCP) tools work in the Mirage framework and provides a step-by-step guide for adding new tools.

## Overview

The Mirage framework uses MCP (Model Context Protocol) to provide extensible tool capabilities to LLM agents. MCP allows agents to interact with external services, APIs, and capabilities through a standardized protocol.

## Architecture

The MCP tools architecture consists of several key components:

```
├── mcp_servers/          # MCP server implementations
├── tool-tests/           # Test files for MCP tools
├── manager.py           # ToolManager - handles tool discovery and execution
├── settings.py          # Configuration and server parameter setup
├── orchestrator.py      # Main orchestration logic
└── prompt_utils.py      # System prompt generation with tool definitions
```

### Key Components

1. **MCP Servers** (`mcp_servers/`): Individual tool implementations
2. **ToolManager** (`manager.py`): Coordinates tool discovery and execution
3. **Configuration** (`settings.py`): Defines which tools are available to which agents
4. **Orchestrator** (`orchestrator.py`): Manages the interaction between LLM and tools
5. **Prompt Utils** (`prompt_utils.py`): Generates system prompts with tool definitions

## How MCP Tools Work

### 1. Tool Discovery Flow

```
Agent Config (YAML) → Settings.py → ToolManager → MCP Servers → Tool Definitions
```

1. Agent configuration (`conf/agent/default.yaml`) specifies which tools are enabled
2. `settings.py` creates MCP server parameters based on the configuration
3. `ToolManager` connects to MCP servers and retrieves tool definitions
4. Tool definitions are included in the system prompt via `prompt_utils.py`

### 2. Tool Execution Flow

```
LLM Request → Orchestrator → ToolManager → MCP Server → Tool Result → LLM Response
```

1. LLM requests a tool call in the standardized format
2. `Orchestrator` parses the tool call and delegates to `ToolManager`
3. `ToolManager` executes the tool call on the appropriate MCP server
4. Tool result is formatted and returned to the LLM

### 3. System Prompt Integration

Tools are automatically included in the system prompt with their definitions:

```
## Server name: tool-vqa
### Tool name: visual_question_answering
Description: Ask question about an image or a video and get the answer with a vision language model.
Input JSON schema: {"type": "object", "properties": {...}, "required": [...]}
```

## Adding a New MCP Tool

### Step 1: Create the MCP Server

Create a new file in `mirage/libs/mirage-contrib/src/mirage/contrib/tools/mcp_servers/`:

```python
# my_new_tool_server.py
import os
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("my-new-tool-server")

# Get environment variables if needed
MY_API_KEY = os.environ.get("MY_API_KEY", "")

@mcp.tool()
async def my_tool_function(input_param: str) -> str:
    """Description of what this tool does.
    
    Args:
        input_param: Description of the input parameter.
    
    Returns:
        Description of what the tool returns.
    """
    
    # Your tool implementation here
    try:
        # Process the input and generate output
        result = f"Processed: {input_param}"
        return result
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Step 2: Add Configuration in Settings

Add your tool configuration to `mirage/apps/reorg-modular-structure/src/mirage_agent/config/settings.py`:

```python
def create_mcp_server_parameters(cfg: DictConfig, agent_cfg: DictConfig):
    """Define and return MCP server configuration list"""
    configs = []
    
    # ... existing code ...
    
    # Add your new tool configuration
    if agent_cfg.get("tools", None) is not None and "tool-my-new-tool" in agent_cfg["tools"]:
        configs.append(
            {
                "name": "tool-my-new-tool",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "mirage.contrib.tools.mcp_servers.my_new_tool_server"],
                    env={
                        "MY_API_KEY": MY_API_KEY,
                        # Add other environment variables as needed
                    },
                ),
            }
        )
    
    # ... rest of the function ...
```

If the `MY_API_KEY` is not defined before, don't forget to introduce it at the beginning of `settings.py` and its `get_env_info()`.

### Step 3: Update Agent Configuration

Add your tool to the agent configuration file (`conf/agent/default.yaml`):

```yaml
# conf/agent/default.yaml
main_agent:
  tools:
    - tool-code
    - tool-vqa
    - tool-my-new-tool  # Add your new tool name here
  max_turns: 20

sub_agents:
  agent-browsing:
    tools:
      - tool-serper-search
      - tool-my-new-tool  # Or add to sub-agents as needed
    max_turns: 20
```

### Step 4: Create Tests

Create a test file in `mirage/libs/mirage-contrib/tests/tool-tests/`:

```python
# test_my_new_tool_server.py
import os
import sys
import asyncio
import pytest
from typing import Dict, Any

from mirage.contrib.tools.manager import ToolManager
from mcp import StdioServerParameters


class TestMyNewToolServer:
    """Test suite for My New Tool MCP Server functionality."""

    def _get_credentials(self) -> Dict[str, str]:
        """Get API credentials, skip test if not available."""
        api_key = os.environ.get("MY_API_KEY")
        if not api_key:
            pytest.skip("MY_API_KEY environment variable not set")

        return {
            "MY_API_KEY": api_key,
        }

    # Use the same way how tools are created as in Mirage framework.
    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        credentials = self._get_credentials()
        tool_configs = [
            {
                "name": "tool-my-new-tool",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "mirage.contrib.tools.mcp_servers.my_new_tool_server"],
                    env=credentials,
                ),
            }
        ]
        return ToolManager(tool_configs)

    # Example test functions:
    @pytest.mark.asyncio
    async def test_tool_definitions_available(self):
        """Test that tool definitions are properly loaded."""
        pass

    @pytest.mark.asyncio
    async def test_my_tool_function(self):
        """Test the main functionality of your tool."""
        pass
        # Add more specific assertions based on your tool's behavior
```

### Step 5: Add Environment Variables

If your tool requires API keys or other configuration:

1. Add them to your `.env` file:
```bash
MY_API_KEY=your_api_key_here
```

2. Add them to `settings.py`:
```python
MY_API_KEY = os.environ.get("MY_API_KEY")
```

Make sure they are passed to the tool.

### Step 6: Test Your Tool

Run the tests to ensure everything works:

```bash
# Run specific tool tests
uv run pytest ./libs/mirage-contrib/tests/tool-tests/test_my_new_tool_server.py -v

# Run all tool tests
uv run pytest mirage/libs/mirage-contrib/tests/tool-tests/ -v
```

## Tool Implementation Best Practices

### 1. Error Handling

Always implement proper error handling:

```python
@mcp.tool()
async def my_tool_function(input_param: str) -> str:
    """Tool description."""
    try:
        # Your logic here
        result = process_input(input_param)
        return result
    except Exception as e:
        return f"Error: {e}"
```

Make sure agent will know what happened during the tool calling. Agent may adjust its behavior according to these error messages.

### 2. Parameter Validation

Validate input parameters:

```python
@mcp.tool()
async def my_tool_function(required_param: str, optional_param: str = "default") -> str:
    """Tool description.
    
    Args:
        required_param: Required parameter description.
        optional_param: Optional parameter description.
    """
    if not required_param:
        return "Error: required_param cannot be empty"
    
    # Process the parameters
    return f"Processed: {required_param}, {optional_param}"
```

### 3. Environment Variables

Use environment variables for configuration:

```python
import os

API_KEY = os.environ.get("MY_API_KEY", "")
BASE_URL = os.environ.get("MY_BASE_URL", "https://api.example.com")

if not API_KEY:
    raise ValueError("MY_API_KEY environment variable is required")
```

### 4. Async/Await

Use async/await for I/O operations:

```python
import aiohttp

@mcp.tool()
async def fetch_data(url: str) -> str:
    """Fetch data from a URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                return await response.text()
    except:
        pass
```

(Don't forget to try except them. Otherwise failed tool call will trigger the process to terminate.)

## Tool Blacklisting

You can blacklist specific tools by adding them to the agent configuration:

```yaml
# conf/agent/default.yaml
main_agent:
  tools:
    - tool-my-new-tool
  tool_blacklist:
    - ["tool-my-new-tool", "specific_function_name"]  # Blacklist specific functions
  max_turns: 20
```

## Tool Categories

### Current Available Tools

1. **Code Execution** (`tool-code`): Execute Python code and shell commands
2. **Vision/VQA** (`tool-vqa`): Visual question answering with images
3. **Audio** (`tool-transcribe`): Audio transcription and processing
4. **Reasoning** (`tool-reasoning`): Enhanced reasoning capabilities
5. **Document Processing** (`tool-markitdown`(old tool)): Convert documents to markdown
6. **Reading** (`tool-reading`): Read and process documents
7. **Search** (`tool-serper-search`(old tool), `tool-searching`): Web search related capabilities

### Tool Naming Convention

- Use prefix `tool-` for all tool names
- Use lowercase with hyphens for multi-word names
- Example: `tool-my-new-feature`

## Sub-Agents and Tool Access

Different sub-agents can have access to different tools:

```yaml
sub_agents:
  agent-browsing:
    tools:
      - tool-serper-search
      - tool-markitdown
    max_turns: 20
    
  agent-coding:
    tools:
      - tool-code
      - tool-reasoning
    max_turns: 20
```

To create sub-agents, you should modify `prompt_utils.py` to define sub-agents' system prompts. Sub-agents should always be named after `agent-`.