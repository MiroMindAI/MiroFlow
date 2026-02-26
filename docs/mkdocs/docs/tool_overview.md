# Tool Overview

MiroFlow provides a comprehensive set of tools that extend agent capabilities through the Model Context Protocol (MCP).

## Available Tools

!!! info "Core Tools"
    - **[Code Execution](tool_python.md)** (`tool-code-sandbox`) - Python and shell execution in secure E2B sandbox
    - **[Searching](tool_searching.md)** (`tool-searching`) - Web search, Wikipedia, Archive.org, and content retrieval
    - **[Searching (Serper)](tool_searching_serper.md)** (`tool-searching-serper` / `tool-serper-search`) - Lightweight Google search via Serper API
    - **[Vision](tool_vqa.md)** (`tool-image-video` / `tool-image-video-os`) - Image analysis and video processing
    - **[Reasoning](tool_reasoning.md)** (`tool-reasoning` / `tool-reasoning-os`) - Advanced logical analysis via high-quality LLMs

!!! note "Additional Tools"
    - **[Reading](tool_reading.md)** (`tool-reading`) - Multi-format document reading and conversion
    - **[Audio](tool_audio.md)** (`tool-audio` / `tool-audio-os`) - Audio transcription and question answering
    - **Jina Scrape** (`tool-jina-scrape`) - URL scraping with LLM-powered information extraction
    - **Web Browsing** (`tool-browsing`) - Automated web browsing
    - **Markdown Conversion** (`tool-markitdown`) - Document to markdown conversion
    - **Serper Sogou Search** (`tool-serper-sogou-search`) - Sogou search via Serper API (for Chinese content)

    See the `config/tool/` directory for complete tool configurations.

## Tool Configuration

Tools are referenced in agent YAML configuration files:

```yaml title="Example Tool Configuration in Agent YAML"
main_agent:
  tools:
    - config/tool/tool-code-sandbox.yaml
    - config/tool/tool-serper-search.yaml
    - config/tool/tool-jina-scrape.yaml
    - config/tool/tool-reading.yaml
```

You can also blacklist specific tools from a tool server:

```yaml title="Tool Blacklist"
tool_blacklist:
  - server: "tool-serper-search"
    tool: "sogou_search"
```

## Quick Setup

Tools require API keys in your `.env` file. See individual tool documentation for detailed setup instructions.

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
