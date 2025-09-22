# Core Concepts

MiroFlow is a flexible framework for building and deploying intelligent agents capable of complex reasoning and tool use.

## Architecture Overview

<div align="center" markdown="1">
  ![MiroFlow Architecture](../assets/miroflow_architecture.png){ width="80%" }
</div>

!!! abstract "Multi-Stage Agentic Process"
    MiroFlow processes user queries through a structured workflow:

    1. **Intent Recognition & Query Augmentation** - LLMs analyze and refine user input
    2. **Planning & Task Orchestration** - Main agent creates execution plans and coordinates sub-agents
    3. **Delegation to Sub-Agents** - Specialized agents handle domain-specific tasks
    4. **Tool Access via MCP Servers** - Agents leverage external capabilities through MCP protocol
    5. **Result Synthesis & Output Alignment** - Final results are synthesized and formatted

---

## Core Components

### Agent System

!!! info "Agent Architecture"
    **Main Agent**: Primary coordinator that receives tasks, creates plans, and manages overall execution. Can use reasoning tools and delegate to sub-agents.

    **Sub-Agents**: Specialized agents for specific domains:

    - **`agent-worker`**: General-purpose agent with comprehensive tool access (search, files, code, media)
    - Each sub-agent has dedicated configurations and can operate independently

### Tool Integration

!!! note "Tool System"
    **Tool Manager**: Connects to MCP servers and manages tool availability

    **Available Tools**:
    
    - **Code Execution**: Python sandbox via E2B integration
    - **Web Search**: Google search with content retrieval
    - **Document Processing**: Multi-format file reading and analysis
    - **Visual Processing**: Image and video analysis
    - **Audio Processing**: Transcription and audio analysis
    - **Enhanced Reasoning**: Advanced reasoning via high-quality LLMs
    
    See [Tool Overview](tool_overview.md) for detailed tool configurations and capabilities.

### LLM Support

!!! tip "Multi-Provider Support"
    Unified interface supporting:

    - **Anthropic Claude** (via Anthropic API, OpenRouter)
    - **OpenAI GPT** (via OpenAI API)
    - **Qwen** (via SGLang)
    - **MiroThinker** (via SGLang)
    - see [LLM Clients Overview](llm_clients_overview.md) for details*



---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI