# Core Concepts

MiroFlow is a flexible framework for building and deploying intelligent agents capable of complex reasoning and tool use.

## Architecture Overview

<div align="center" markdown="1">
  ![MiroFlow Architecture](assets/miroflow_architecture.png){ width="80%" }
</div>

!!! abstract "Agentic Process"
    MiroFlow processes user queries through a structured workflow:

    1. **Input Processing** - File content pre-processing, hint generation, and message formatting
    2. **Iterative Reasoning with Rollback** - The agent iteratively reasons, plans, and executes tool calls with automatic rollback on failures
    3. **Tool Access via MCP Servers** - Agents leverage external capabilities (search, code execution, file reading, etc.) through the MCP protocol
    4. **Output Processing** - Results are summarized and final answers are extracted (regex-based or LLM-based)

---

## Core Components

### Agent System

!!! info "Agent Architecture"
    **IterativeAgentWithToolAndRollback**: The primary agent type that receives tasks, iteratively reasons and calls tools, with automatic rollback on consecutive failures. Key parameters:

    - `max_turns`: Maximum reasoning/tool-calling iterations
    - `max_consecutive_rollbacks`: Maximum consecutive rollbacks before stopping
    - Configurable tools, prompts, and LLM providers

### Tool Integration

!!! note "Tool System"
    **Tool Manager**: Connects to MCP servers and manages tool availability. Tools are configured via YAML files in `config/tool/`.

    **Available Tools**:

    - **Code Execution** (`tool-code-sandbox`): Python sandbox via E2B integration
    - **Web Search** (`tool-searching`, `tool-serper-search`, `tool-searching-serper`): Google search with content retrieval
    - **URL Scraping** (`tool-jina-scrape`): URL scraping with LLM-powered info extraction
    - **Document Processing** (`tool-reading`): Multi-format file reading and analysis
    - **Visual Processing** (`tool-image-video`, `tool-image-video-os`): Image and video analysis
    - **Audio Processing** (`tool-audio`, `tool-audio-os`): Transcription and audio analysis
    - **Enhanced Reasoning** (`tool-reasoning`, `tool-reasoning-os`): Advanced reasoning via high-quality LLMs
    - **Web Browsing** (`tool-browsing`): Automated web browsing
    - **Markdown Conversion** (`tool-markitdown`): Document to markdown conversion

    See [Tool Overview](tool_overview.md) for detailed tool configurations and capabilities.

### Input/Output Processors

!!! note "Processing Pipeline"
    **Input Processors** (run before agent execution):

    - `FileContentPreprocessor`: Pre-processes attached file content
    - `InputHintGenerator`: Generates task hints using an LLM
    - `InputMessageGenerator`: Formats the initial message for the agent

    **Output Processors** (run after agent execution):

    - `SummaryGenerator`: Summarizes the agent's conversation
    - `RegexBoxedExtractor`: Extracts `\boxed{}` answers via regex
    - `FinalAnswerExtractor`: Extracts final answers using an LLM
    - `ExceedMaxTurnSummaryGenerator`: Generates summary when max turns are exceeded

### LLM Support

!!! tip "Multi-Provider Support"
    Unified interface supporting:

    - **Anthropic Claude** (via Anthropic API or OpenRouter)
    - **OpenAI GPT** (GPT-4o, GPT-5 via OpenAI API)
    - **DeepSeek** (via OpenRouter or OpenAI-compatible API)
    - **MiroThinker** (via SGLang, open-source)
    - **Kimi K2.5** (via OpenAI-compatible API)
    - **Any OpenAI-compatible API** (via generic OpenAI/OpenRouter clients)
    - See [LLM Clients Overview](llm_clients_overview.md) for details

### Component Registry

!!! info "Registry System"
    MiroFlow uses a unified registration mechanism for dynamically discovering and loading components:

    - **Agents**: Registered via `@register(ComponentType.AGENT, "name")`
    - **IO Processors**: Registered via `@register(ComponentType.IO_PROCESSOR, "name")`
    - **LLM Clients**: Registered via `@register(ComponentType.LLM, "name")`
    - **Tools**: Discovered dynamically via MCP protocol (not registered in code)
    - **Skills**: Discovered via filesystem scanning

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
