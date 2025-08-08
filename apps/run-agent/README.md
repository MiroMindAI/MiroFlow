# Mirage Agent - Modular Structure

This project is an example of a modular agent structure, utilizing Hydra for advanced configuration management.

## 快速试验

You may refer to `scripts/exmamples` to run simple tests.

## 运行程序

This project uses `uv` for environment and package management.

### 基本运行

To run the main application with the default configuration (as defined in `conf/config.yaml`), use the following command:

```bash
uv run main.py
```

### 使用 Hydra 进行配置

Hydra allows for powerful configuration overrides directly from the command line.

**1. 切换 LLM 配置:**

You can switch the entire language model configuration by specifying the `llm` group. For example, to use the `gemini` configuration instead of the default `gpt-4`:

```bash
uv run main.py llm=gemini
```

Available LLM configurations can be found in `conf/llm/`.

**2. 覆盖单个参数:**

Any parameter in the configuration can be overridden. For example, to change the temperature of the `gemini` model:

```bash
uv run main.py llm=gemini llm.temperature=0.9
```

**3. 运行基准测试:**

The benchmark runner also uses Hydra. To run a benchmark, specify the `benchmark` group:

```bash
uv run benchmarks/common_benchmark.py benchmark=gaia
```


## 配置结构

The configuration for this application resides in the `conf/` directory, following Hydra conventions:

- `conf/config.yaml`: The main entry point for configuration. It defines the default composition of configuration groups.
- `conf/llm/`: Contains configurations for different language models (e.g., `gpt-4.yaml`, `gemini.yaml`).
- `conf/agent/`: Contains configurations for different agent setups.
- `conf/benchmark/`: Contains configurations for different benchmark tasks.
- `conf/pricing/`: Contains configurations for different models' price.
