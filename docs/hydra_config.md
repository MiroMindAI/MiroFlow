## Hydra config system
### Config File Structure

```
MiroFlow/libs/miroflow/src/miroflow/prebuilt/config
├── config.yaml              # Main configuration with defaults
├── agent/                   # Agent configurations (tools, limits)
├── benchmark/               # Benchmark configurations (datasets, execution)
└── llm/                     # Language model configurations (providers, models)
```

### Usage

Run with default configuration:
```bash
cd MiroFlow/apps/run-agent
uv run main.py common-benchmark
```

Default configuration is defined in  
`MiroFlow/libs/miroflow/src/miroflow/prebuilt/config/config.yaml`:

```yaml
# conf/config.yaml
defaults:
  - llm: claude_openrouter
  - agent: miroflow
  - benchmark: gaia-validation
  - pricing: _default

# Other configurations...
```

| Component  | Default Value         | File Path                                                                 |
|------------|----------------------|---------------------------------------------------------------------------|
| LLM        | `claude_openrouter`  | `libs/miroflow/src/miroflow/prebuilt/config/llm/claude_openrouter.yaml`                                   |
| Agent      | `miroflow`           | `libs/miroflow/src/miroflow/prebuilt/config/agent/miroflow.yaml`                        |
| Benchmark  | `gaia-validation`    | `libs/miroflow/src/miroflow/prebuilt/config/benchmark/gaia-validation.yaml`                                       |


### Override Configurations

#### Component Override
Switch between existing configurations using the filename (without `.yaml`):
```bash
uv run main.py common-benchmark llm=<filename> agent=<filename> benchmark=<filename>
```

For example, if you have `conf/llm/claude_openrouter.yaml`, use `llm=claude_openrouter`


#### Parameter Override
Override specific parameters:
```bash
cd MiroFlow/apps/run-agent
uv run main.py common-benchmark llm.temperature=0.1 agent.main_agent.max_turns=30
```

### Create Custom Configurations

1. **Create new config file** in the appropriate subdirectory (e.g., `conf/llm/my_config.yaml`)
2. **Inherit from defaults** using Hydra's composition:
   ```yaml
   defaults:
     - default  # Inherit base configuration
     - _self_    # Allow self-overrides
   
   # Your custom parameters
   parameter: value
   ```
3. **Use your config**: `uv run main.py common-benchmark component=my_config`

## Recommended: Use scripts to run experiments.
We recommend using the scripts provided under `./apps/run-agent/scripts`, as script files are much easier to read, maintain, and customize compared to single-line commands.

A script file example is as follows:
```bash
#!/bin/bash

# Number of runs for the benchmark
NUM_RUNS=4 
# The parallelization concurrent number for a single run (total concurrent = NUM_RUNS * MAX_CONCURRENT)
MAX_CONCURRENT=15 
# Benchmark name (must match the benchmark's config file name)
BENCHMARK_NAME="gaia-validation"
# Agent set name (must match the agent's config file name)
AGENT_SET="claude03_claude_dual"
# Set to true to add a random message ID to all messages sent to the LLM
ADD_MESSAGE_ID="true"
# When set to a positive finite number, all main and sub agents will have turn limits. Set to -1 for no limit.
MAX_TURNS=-1

# Automatically enable Chinese context - if BENCHMARK_NAME contains xbench or -zh
if [[ $BENCHMARK_NAME == "xbench-ds" ]] || [[ $BENCHMARK_NAME == "browsecomp-zh" ]]; then
    export CHINESE_CONTEXT="true"
    echo "检测到中文相关基准测试，已启用中文上下文：CHINESE_CONTEXT=true"
fi

# These options are used to filter Google search results.
# export REMOVE_SNIPPETS="true"
# export REMOVE_KNOWLEDGE_GRAPH="true"
# export REMOVE_ANSWER_BOX="true"

# Define the results directory to save outputs
RESULTS_DIR="logs/${BENCHMARK_NAME}/${AGENT_SET}"

echo "Starting $NUM_RUNS runs of the evaluation..."
echo "Results will be saved in: $RESULTS_DIR"

mkdir -p "$RESULTS_DIR"

# For loop to start NUM_RUNS experiments in parallel.
for i in $(seq 1 $NUM_RUNS); do
    RUN_ID="run_$i"
    (
        # You can override any parameters you want here
        uv run main.py common-benchmark \
            benchmark=$BENCHMARK_NAME \
            agent=$AGENT_SET \
            agent.add_message_id=$ADD_MESSAGE_ID \
            agent.main_agent.max_turns=$MAX_TURNS \
            agent.sub_agents.agent-worker.max_turns=$MAX_TURNS \
            benchmark.execution.max_tasks=null \
            benchmark.execution.max_concurrent=$MAX_CONCURRENT \
            benchmark.execution.pass_at_k=1 \
            output_dir="$RESULTS_DIR/$RUN_ID" \
            hydra.run.dir=${RESULTS_DIR}/$RUN_ID \
            > "$RESULTS_DIR/${RUN_ID}_output.log" 2>&1
    ) &
    
    sleep 2
done

echo "All $NUM_RUNS runs have been launched in parallel"
echo "Waiting for all runs to complete..."

wait

echo "=========================================="
echo "All $NUM_RUNS runs completed!"
echo "=========================================="

# Calculate average scores
echo "Calculating average scores..."
uv run main.py avg-score "$RESULTS_DIR"

echo "=========================================="
echo "Multiple runs evaluation completed!"
echo "Check results in: $RESULTS_DIR"
echo "Check individual run logs: $RESULTS_DIR/run_*_output.log"
echo "=========================================="
```