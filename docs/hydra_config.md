
### Structure

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
     - _default  # Inherit base configuration
     - _self_    # Allow self-overrides
   
   # Your custom parameters
   parameter: value
   ```
3. **Use your config**: `uv run main.py common-benchmark component=my_config`
