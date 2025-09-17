# Adding New Tools

## What This Does
Extend the agent’s functionality by introducing a new tool. Each tool is implemented as an MCP server and registered via configuration.

## Implementation Steps

### 1. Create MCP Server
Create a new file `src/tool/mcp_servers/new-mcp-server.py` that implements the tool’s core logic.  

```python
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

> Tool schemas are automatically generated from `docstrings` and `hints` via the FastMCP protocol.


### 2. Create Tool Config
Add a new config file at `config/tools/new-tool-name.yaml`:

```yaml
name: "new-tool-name"
tool_command: "python"
args:
  - "-m"
  - "src.tool.mcp_servers.new-mcp-server"  # Match the server file created above
```


### 3. Register Tool in Agent Config
Enable the new tool inside your agent config (e.g., `config/agent-with-new-tool.yaml`):

```yaml
main_agent:
  ...
  tool_config:
    - tool-reasoning
    - new-tool-name   # 👈 Add your new tool here
  ...
sub_agents:
  agent-worker:
    ...
    tool_config:
      - tool-searching
      - tool-image-video
      - tool-reading
      - tool-code
      - tool-audio
      - new-tool-name # 👈 Add your new tool here
    ...
```


## Examples
- `tool-reasoning` – reasoning utilities  
- `tool-image-video` – visual understanding  
- `new-tool-name` – your custom tool  

---

**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI  
