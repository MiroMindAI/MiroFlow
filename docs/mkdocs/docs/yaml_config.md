
# 📋 YAML Configuration Guide

MiroFlow uses a flexible Hydra-based configuration system that allows you to customize every aspect of your AI agents. This guide explains all configuration features and how to use them effectively.

---

## 🏗️ Configuration Structure

!!! info "Current File Organization"
    The configuration system is organized hierarchically for easy management.

```bash title="Configuration Directory Structure"
config/
├── agent_quickstart_1.yaml       # Quick start configuration
├── agent_gaia-validation.yaml    # GAIA benchmark configuration  
├── agent_mirothinker.yaml        # MiroThinker model configuration
├── agent_prompts/                # Agent prompt classes
│   ├── main_agent_prompt_gaia.py # GAIA-specific prompts
│   ├── main_boxed_answer.py      # Boxed answer extraction
│   └── sub_worker.py            # Sub-agent prompts
├── benchmark/                    # Benchmark configurations
│   ├── default.yaml              # Default benchmark settings
│   └── gaia-validation.yaml      # GAIA validation benchmark
├── tool/                         # Tool configurations
│   ├── tool-reasoning.yaml       # Enhanced reasoning tool
│   ├── tool-searching.yaml       # Web search capabilities
│   ├── tool-reading.yaml         # Document processing
│   ├── tool-code.yaml           # Code execution
│   ├── tool-image-video.yaml    # Visual content analysis
│   └── tool-audio.yaml          # Audio processing
└── no-in-use-*/                  # Archive of legacy configurations
```

---

## 🚀 Quick Start Usage

!!! example "Basic Usage Examples"

    **Simple Agent Execution**
    
    ```bash title="Basic Command"
    # Run with a specific agent configuration
    uv run main.py trace --config_file_name=agent_quickstart_1 --task="Your task here"
    
    # Run with file input
    uv run main.py trace --config_file_name=agent_quickstart_1 --task="Analyze this file" --task_file_name="data/file.xlsx"
    ```
    
    **Parameter Override**
    
    ```bash title="Dynamic Configuration"
    # Override specific parameters on the fly
    uv run main.py trace --config_file_name=agent_gaia-validation \
        main_agent.llm.temperature=0.1 \
        main_agent.max_turns=30 \
        --task="Your task"
    ```

---

## ⚙️ Configuration Features

### 🤖 Agent Configuration

!!! note "Main Agent Settings"

    **Core Configuration Options**
    
    - **`prompt_class`**: Defines the prompt template and behavior
      - `MainAgentPromptBoxedAnswer`: Basic boxed answer extraction
      - `MainAgentPrompt_GAIA`: GAIA benchmark optimized prompts
    - **`llm`**: Language model configuration (inline or reference)
    - **`tool_config`**: List of tools available to the main agent
    - **`max_turns`**: Maximum conversation turns (-1 = unlimited)
    - **`max_tool_calls_per_turn`**: Limit tool calls per turn (default: 10)

    **Sub-Agent Configuration**
    
    - **`agent-worker`**: General-purpose sub-agent with comprehensive tools
    - **Individual LLM settings**: Each sub-agent can use different models
    - **Specialized tool sets**: Customize tools per sub-agent role

    **Advanced Features**
    
    - **`add_message_id`**: Add unique IDs to messages for tracking
    - **`chinese_context`**: Enable Chinese language optimization
    - **`keep_tool_result`**: Control tool result retention (-1 = keep all)

### 🔧 LLM Configuration

!!! abstract "LLM Provider Settings"

    **Provider Configuration Example**
    
    ```yaml title="LLM Configuration"
    llm:
      provider_class: "ClaudeOpenRouterClient"  # or "MiroThinkerSGLangClient"
      model_name: "anthropic/claude-3.7-sonnet"
      temperature: 0.3
      max_tokens: 32000
      async_client: true
    ```

    **Available Providers**
    
    - **Claude (OpenRouter)**: `ClaudeOpenRouterClient`
    - **MiroThinker**: `MiroThinkerSGLangClient`
    - **OpenAI**: `GPTOpenAIClient`
    - **DeepSeek**: `DeepSeekNewAPIClient`

    **Model Parameters**
    
    - **`temperature`**: Creativity/randomness (0.0-1.0)
    - **`top_p`**: Nucleus sampling parameter
    - **`max_tokens`**: Maximum response length
    - **`top_k`**: Top-k sampling (-1 = disabled)

### 🛠️ Tool Configuration

!!! tip "Available Tools & Environment Setup"

    **Available Tools**
    
    - **`tool-reasoning`**: Enhanced reasoning with high-quality models
    - **`tool-searching`**: Web search with Google/Serper integration
    - **`tool-reading`**: Document processing (PDF, DOCX, TXT, etc.)
    - **`tool-code`**: Python code execution in E2B sandbox
    - **`tool-image-video`**: Visual content analysis
    - **`tool-audio`**: Audio transcription and processing

    **Tool Environment Variables**
    
    ```yaml title="tool-searching.yaml"
    # tool-searching.yaml
    env:
      SERPER_API_KEY: "${oc.env:SERPER_API_KEY}"
      JINA_API_KEY: "${oc.env:JINA_API_KEY}"
      REMOVE_SNIPPETS: "${oc.env:REMOVE_SNIPPETS,false}"
    ```

### 🎯 Processing Features

!!! success "Advanced Processing Options"

    **Input Processing**
    
    - **`o3_hint`**: Use O3 model for task hint generation
    - Advanced prompt engineering for better task understanding

    **Output Processing**
    
    - **`o3_final_answer`**: Use O3 model for final answer extraction
    - Boxed answer format for benchmark compliance
    - Intelligent result synthesis

---

## 🔧 Creating Custom Configurations

!!! example "Configuration Examples"

    === "Basic Custom Agent"

        ```yaml title="Custom Agent Configuration"
        defaults:
          - benchmark: gaia-validation
          - override hydra/job_logging: none
          - _self_
        
        main_agent:
          prompt_class: MainAgentPromptBoxedAnswer
          llm:
            provider_class: "ClaudeOpenRouterClient"
            model_name: "anthropic/claude-3.7-sonnet"
            temperature: 0.5  # Custom temperature
          tool_config:
            - tool-reasoning  # Add reasoning capability
          max_turns: 15      # Custom turn limit
        
        sub_agents:
          agent-worker:
            prompt_class: SubAgentWorkerPrompt
            tool_config:
              - tool-reading   # Document processing only
            max_turns: 10
        ```

    === "Multi-Tool Configuration"

        ```yaml title="Advanced Tool Setup"
        main_agent:
          tool_config:
            - tool-reasoning    # Enhanced reasoning
            - tool-searching    # Web search
            
        sub_agents:
          agent-worker:
            tool_config:
              - tool-reading    # Document processing
              - tool-code       # Code execution
              - tool-image-video # Visual analysis
              - tool-audio      # Audio processing
        ```

    === "Environment-Specific Settings"

        ```yaml title="Environment Configurations"
        # Development configuration
        main_agent:
          llm:
            temperature: 0.7     # Higher creativity for exploration
          max_turns: -1          # Unlimited turns
          add_message_id: true   # Enable debugging
        
        # Production configuration  
        main_agent:
          llm:
            temperature: 0.3     # Lower temperature for consistency
          max_turns: 20          # Controlled turn limit
          add_message_id: false  # Disable for performance
        ```

---

## 📊 Benchmark Integration

!!! note "Benchmark Configuration Examples"

    === "GAIA Validation"

        ```yaml title="GAIA Benchmark Configuration"
        defaults:
          - benchmark: gaia-validation
        
        main_agent:
          prompt_class: MainAgentPrompt_GAIA
          input_process:
            o3_hint: true          # Use O3 hints for better performance
          output_process:
            o3_final_answer: true  # Extract answers with O3
        ```

    === "Custom Benchmark"

        ```yaml title="config/benchmark/my-benchmark.yaml"
        # config/benchmark/my-benchmark.yaml
        name: "my-benchmark"
        data:
          data_dir: "${oc.env:DATA_DIR,data}/my-data"
        execution:
          max_tasks: 100         # Limit task count
          max_concurrent: 5      # Parallel execution
          pass_at_k: 1          # Success criteria
        ```

---

## 📜 Script-Based Execution

!!! tip "Script-Based Approach"
    We recommend using the scripts provided under `./scripts/`, as script files are much easier to read, maintain, and customize compared to single-line commands.

!!! example "Benchmark Evaluation Script"

    ```bash title="scripts/benchmark_evaluation.sh"
    #!/bin/bash
    
    # Configuration
    NUM_RUNS=3                              # Number of parallel runs
    MAX_CONCURRENT=10                       # Concurrent tasks per run
    BENCHMARK_NAME="gaia-validation"        # Benchmark configuration
    AGENT_CONFIG="agent_gaia-validation"    # Agent configuration
    ADD_MESSAGE_ID="true"                   # Enable message tracking
    MAX_TURNS=-1                           # Unlimited turns (-1)
    
    # Auto-detect Chinese benchmarks
    if [[ $BENCHMARK_NAME == "xbench-ds" ]] || [[ $BENCHMARK_NAME == "browsecomp-zh" ]]; then
        export CHINESE_CONTEXT="true"
        echo "Detected Chinese benchmark, enabling Chinese context"
    fi
    
    # Google search filtering (optional)
    # export REMOVE_SNIPPETS="true"
    # export REMOVE_KNOWLEDGE_GRAPH="true" 
    # export REMOVE_ANSWER_BOX="true"
    
    RESULTS_DIR="logs/${BENCHMARK_NAME}/${AGENT_CONFIG}"
    echo "Starting evaluation with $NUM_RUNS parallel runs..."
    
    # Launch parallel experiments
    for i in $(seq 1 $NUM_RUNS); do
        RUN_ID="run_$i"
        (
            uv run main.py trace \
                --config_file_name=$AGENT_CONFIG \
                --benchmark_name=$BENCHMARK_NAME \
                --max_concurrent=$MAX_CONCURRENT \
                --output_dir="$RESULTS_DIR/$RUN_ID" \
                > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1
        ) &
        sleep 2
    done
    
    wait
    echo "All runs completed! Check results in: $RESULTS_DIR"
    ```

---

## 🔧 Advanced Configuration Tips

!!! warning "Environment Variable Management"

    ```bash title=".env file example"
    # .env file example
    OPENROUTER_API_KEY=your_key_here
    SERPER_API_KEY=your_serper_key
    JINA_API_KEY=your_jina_key
    E2B_API_KEY=your_e2b_key
    
    # Optional: Customize search behavior
    REMOVE_SNIPPETS=false
    REMOVE_KNOWLEDGE_GRAPH=false
    REMOVE_ANSWER_BOX=false
    CHINESE_CONTEXT=false
    ```

!!! success "Configuration Categories"

    === "Configuration Validation"

        ```yaml title="Validation Guidelines"
        # Add validation to your configs
        main_agent:
          llm:
            temperature: 0.3        # Must be 0.0-1.0
            max_tokens: 32000       # Model-specific limits
          max_turns: 20             # Positive integer or -1
          tool_config:              # Must be valid tool names
            - tool-reasoning
        ```

    === "Performance Optimization"

        ```yaml title="High-Performance Settings"
        # High-performance configuration
        main_agent:
          llm:
            async_client: true      # Enable async processing
            max_tokens: 8192        # Reasonable token limit
          max_tool_calls_per_turn: 5  # Limit tool calls for speed
        
        benchmark:
          execution:
            max_concurrent: 15      # Parallel execution
            pass_at_k: 1           # Single attempt per task
        ```

    === "Debugging Configuration"

        ```yaml title="Debug-Friendly Settings"
        # Debug-friendly settings
        main_agent:
          add_message_id: true      # Track message flow
          keep_tool_result: -1      # Keep all tool results
          max_turns: -1             # Unlimited exploration
        
        sub_agents:
          agent-worker:
            max_turns: -1           # Unlimited sub-agent turns
        ```

---

## 🎯 Configuration Best Practices

!!! tip "Best Practices Guide"

    **1. Start Simple**
    
    Begin with basic configurations like `agent_quickstart_1.yaml` and add complexity gradually.

    **2. Environment Separation**
    
    - **Development**: Higher temperature, unlimited turns, debugging enabled
    - **Testing**: Moderate settings with turn limits
    - **Production**: Conservative settings, optimized for performance

    **3. Tool Selection**
    
    Choose tools based on your use case:
    
    - **Research Tasks**: `tool-searching` + `tool-reasoning`
    - **Document Analysis**: `tool-reading` + `tool-reasoning`
    - **Code Tasks**: `tool-code` + `tool-reasoning`
    - **Multimedia**: `tool-image-video` + `tool-audio`

    **4. Resource Management**
    
    - Monitor `max_concurrent` to avoid API rate limits
    - Set reasonable `max_tokens` for cost control
    - Use `max_turns` to prevent infinite loops

    **5. API Key Security**
    
    - Always use environment variables for API keys
    - Never commit API keys to version control
    - Use different keys for development and production

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI
