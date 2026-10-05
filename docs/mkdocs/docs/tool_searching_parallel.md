# Parallel Search MCP

`tool-searching-parallel` exposes the free, keyless Parallel Search MCP service
at `https://search.parallel.ai/mcp` through MiroFlow's existing stdio tool path.
It forwards the service's tool descriptions, schemas and text results, including
search and page fetching. No Parallel API key or additional dependency is needed.
The tool configuration forwards optional `HTTPS_PROXY`, `HTTP_PROXY`, `NO_PROXY`
and `SSL_CERT_FILE` environment settings for networks that require a proxy or
custom CA bundle. It does not forward provider API keys.
Requests identify the caller as MiroFlow with a `User-Agent` header.

## Quickstart

From the repository root, install the project dependencies and configure the
OpenRouter key used by the existing search quickstart:

```bash
uv sync
cp .env.template .env
# Set OPENROUTER_API_KEY in .env.
uv run main.py trace --config_file_name=agent_quickstart_parallel_search \
  --task="Search for the Python asyncio documentation and explain what asyncio.run does, with a source URL."
```

The search service needs no key; the agent's language model still requires its
normal credentials. Network access to `search.parallel.ai` is required. Service
errors and availability affect this tool, as with other remote tools.

## Select the tool in another agent

Add `tool-searching-parallel` to the desired agent's `tool_config` list, following
the [tool contribution guide](contribute_tools.md). For example:

```yaml
main_agent:
  tool_config:
    - tool-searching-parallel
```

The name loads `config/tool/tool-searching-parallel.yaml`, which starts
`src.tool.mcp_servers.parallel_search_mcp_server`. That module bridges stdio to
Parallel's Streamable HTTP endpoint using the existing FastMCP dependency.
Tool discovery and execution use `ToolManager`, including its existing blacklist
and result handling. There is no change to the default agents or Serper/Jina
configuration. Selecting this tool is optional, and it can coexist with other
tools in the same list.

## Local validation

```bash
uv run python -m unittest discover -s tests -p 'test_parallel_search.py'
```

These tests use a local MCP server and a scripted language model response to
check agent configuration, discovery, execution, headers, errors, exclusions and
a final answer through the orchestrator, without external credentials.
