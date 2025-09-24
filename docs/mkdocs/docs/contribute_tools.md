# Contributing New Tools

MiroFlow's extensible tool system allows you to add custom functionality by implementing new MCP (Model Context Protocol) servers. Each tool extends the agent's capabilities and can be easily integrated into the framework.

## Overview

!!! info "What This Does"
    Extend the agent's functionality by introducing a new tool. Each tool is implemented as an MCP server and registered via configuration, enabling agents to access new capabilities seamlessly.

---

## Implementation Steps

### Step 1: Create MCP Server

Create a new file `src/tool/mcp_servers/new-mcp-server.py` that implements the tool's core logic.

```python title="src/tool/mcp_servers/new-mcp-server.py"
from fastmcp import FastMCP

# Initialize FastMCP server
mcp = FastMCP("new-mcp-server")

@mcp.tool()
async def tool_name(param: str) -> str:
    """
    Explanation of the tool, its parameters, and return value.
    """
    tool_result = ...  # Your logic here
    return tool_result

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

!!! tip "Automatic Schema Generation"
    Tool schemas are automatically generated from `docstrings` and `type hints` via the FastMCP protocol.

### Step 2: Create Tool Configuration

Add a new configuration file at `config/tool/new-tool-name.yaml`:

```yaml title="config/tool/new-tool-name.yaml"
name: "new-tool-name"
tool_command: "python"
args:
  - "-m"
  - "src.tool.mcp_servers.new-mcp-server"  # Match the server file created above
```

### Step 3: Register Tool in Agent Configuration

Enable the new tool inside your agent configuration (e.g., `config/agent-with-new-tool.yaml`):

```yaml title="config/agent-with-new-tool.yaml"
main_agent:
  # ... other configuration ...
  tool_config:
    - tool-reasoning
    - new-tool-name   # 👈 Add your new tool here
  # ... other configuration ...

sub_agents:
  agent-worker:
    # ... other configuration ...
    tool_config:
      - tool-searching
      - tool-image-video
      - tool-reading
      - tool-code
      - tool-audio
      - new-tool-name # 👈 Add your new tool here
    # ... other configuration ...
```

---


!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI