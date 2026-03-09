# Core Concepts

MiroFlow is a flexible framework for building and deploying intelligent agents capable of complex reasoning and tool use.

## Architecture Overview

<div align="center" markdown="1">
  ![MiroFlow Architecture](assets/miroflow_architecture_v1.7.png){ width="100%" }
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
    MiroFlow provides a modular agent hierarchy built on `BaseAgent`:

    **IterativeAgentWithToolAndRollback**: The primary agent type that receives tasks, iteratively reasons and calls tools, with automatic rollback on consecutive failures. Key parameters:

    - `max_turns`: Maximum reasoning/tool-calling iterations
    - `max_consecutive_rollbacks`: Maximum consecutive rollbacks before stopping
    - `max_duplicate_rollbacks`: Maximum duplicate tool-call rollbacks before stopping
    - Configurable tools, prompts, and LLM providers

    **SequentialAgent**: Composes multiple sub-modules in sequence, passing `AgentContext` between them. Used for building input/output processing pipelines and multi-step workflows.

#### Smart Rollback & Retry

!!! warning "Automatic Error Recovery"
    The iterative agent automatically detects and recovers from common LLM output issues:

    - **Format errors**: Malformed tool calls or invalid JSON arguments
    - **Truncated output**: Incomplete responses due to token limits
    - **Refusals**: LLM refusing to complete the task
    - **Duplicate tool calls**: Repeated identical tool invocations that indicate the agent is stuck

    On detection, the agent rolls back the failed turn and retries with accumulated failure feedback, giving the LLM context about what went wrong. This dramatically improves robustness in production.

#### Agent Graph & Multi-Agent Composition

!!! tip "Multi-Agent Orchestration"
    MiroFlow supports composing agents into hierarchical graphs. A main agent can delegate subtasks to sub-agents, each with their own LLM, tools, and prompts.

    **How it works:**

    - Sub-agents are defined in the YAML config and referenced via `sub_agents` field
    - Sub-agents are exposed to the parent agent as callable tools (e.g., `agent-worker`)
    - Each sub-agent can have its own sub-agents, enabling multi-level hierarchies
    - Agents share context through `AgentContext`, a dict-based object for inter-agent communication

    **Example config** (`config/agent_quickstart_graph.yaml`):
    ```yaml
    main_agent:
      type: IterativeAgentWithTool
      sub_agents:
        agent-worker: ${agent-subagent-1}

    agent-subagent-1:
      type: IterativeAgentWithTool
      sub_agents:
        agent-worker: ${agent-subagent-3}

    agent-subagent-3:
      type: IterativeAgentWithTool
      tools:
        - config/tool/tool-code-sandbox.yaml
        - config/tool/tool-serper-search.yaml
    ```

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

!!! tip "Model-Agnostic — One-Line Model Switching"
    MiroFlow is model-agnostic: change `provider_class` and `model_name` in YAML and the entire framework — tools, prompts, rollback logic — works with your chosen model. Unified interface supporting:

    - **Anthropic Claude** (via Anthropic API or OpenRouter)
    - **OpenAI GPT** (GPT-4o, GPT-5 via OpenAI API)
    - **DeepSeek** (via OpenRouter or OpenAI-compatible API)
    - **MiroThinker** (via SGLang, open-source)
    - **Kimi K2.5** (via OpenAI-compatible API)
    - **Any OpenAI-compatible API** (via generic OpenAI/OpenRouter clients)
    - See [LLM Clients Overview](llm_clients_overview.md) for details

### Skill System

!!! example "Markdown-Based Skill Definition"
    Skills are reusable instruction sets that guide the agent on how to handle specific types of tasks. Each skill is defined by a `SKILL.md` file with YAML frontmatter and markdown instructions.

    **Skill structure:**
    ```
    miroflow/skill/skills/
    └── simple_file_understanding/
        └── SKILL.md
    ```

    **Example `SKILL.md`:**
    ```markdown
    ---
    name: simple_file_understanding
    description: Understand and analyze CSV files. Use when the task
                 involves reading, parsing, or answering questions
                 about data in a CSV file.
    ---

    # simple_file_understanding

    ## Instructions
    When a task involves a CSV file, follow this workflow:
    1. Use the `read_file` tool to load the file content.
    2. Identify column headers, data types, and row count.
    3. Answer the question based on the data.
    ```

    **Key features:**

    - **Auto-discovery**: Skills are automatically discovered by scanning configured directories
    - **Sandboxed execution**: Python skills run in a sandboxed environment for safety
    - **Whitelisting**: Restrict which skills are available in production via `allowed_skill_ids`
    - **MCP integration**: Skills are exposed to the agent as callable tools through the Skill MCP Server

    Enable skills in your agent config:
    ```yaml
    main_agent:
      skill:
        skill_dirs:
          - miroflow/skill/skills
        allow_python_skills: true
    ```

### Component Registry

!!! info "Plugin Architecture"
    MiroFlow uses a unified registration mechanism for dynamically discovering and loading components. This enables a plugin-like architecture where new agents, IO processors, and LLM clients can be added without modifying core code.

    **Register a new component:**
    ```python
    from miroflow.registry import register, ComponentType

    @register(ComponentType.AGENT, "MyCustomAgent")
    class MyCustomAgent(BaseAgent):
        async def run_internal(self, ctx):
            # Your custom logic here
            return ctx
    ```

    **Supported component types:**

    - **Agents**: `@register(ComponentType.AGENT, "name")` — custom agent implementations
    - **IO Processors**: `@register(ComponentType.IO_PROCESSOR, "name")` — input/output pipeline stages
    - **LLM Clients**: `@register(ComponentType.LLM, "name")` — new LLM provider integrations
    - **Tools**: Discovered dynamically via MCP protocol (not registered in code)
    - **Skills**: Discovered via filesystem scanning (see [Skill System](#skill-system))

    The registry features **thread-safe lazy loading** — modules are only imported when their components are first requested.

### Prompt Management

!!! note "Zero-Code Prompt Configuration"
    Agent prompts are managed through **YAML + Jinja2 templates**, not Python code. This means you can tune agent behavior by editing config files — no code changes or redeployment needed.

    **Prompt config structure** (`config/prompts/*.yaml`):
    ```yaml
    template:
      initial_user_text:
        components:
          - task_description
          - task_guidance
          - file_input_prompt
        task_description: |
          {{ task_description }}
        file_input_prompt: |
          {% if file_input is defined and file_input is not none %}
          A {{ file_input.file_type }} file '{{ file_input.file_name }}'
          is associated with this task.
          {% endif %}
    ```

    The `PromptManager` loads these templates and renders them with runtime context variables, supporting conditional sections, loops, and template composition.

---

!!! info "Documentation Info"
    **Last Updated:** March 2026 · **Doc Contributor:** Team @ MiroMind AI
