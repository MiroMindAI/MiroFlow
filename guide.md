## Git 管理
- 开源项目的工作流一般都是 fork + 提PR 
- 一个分支本质上是代码历史中指向某个commit的指针
- feature/monitor branch: 跑benchmark的时候监控中间过程
- upstream

流程：fork repo -> 创建feature branch -> 提PR -> 通过后merge到自己repo的main

## 简便设置
Edit bash files and python files to run monitoring easily

## Reproducing GAIA Validation Benchmark Results

**Prepara GAIA vaidation dataset:**
```bash
cd data
wget https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/gaia-val.zip
unzip gaia-val.zip
# Unzip passcode: pf4*
```

**API key configuration:**
```bash
touch .env
nano .env
```

**Run GAIA validation with Claude 3.7 Sonnet**

```bash
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation_claude37sonnet \
  output_dir="logs/gaia-validation-claude37sonnet/$(date +"%Y%m%d_%H%M")"
  ```

**Run GAIA validation with integrated web monitoring:**

```bash
uv run main.py run-gaia-with-monitor \
  --config_file_name=agent_gaia-validation_claude37sonnet \
  --output_dir="logs/gaia-validation-claude37sonnet/$(date +"%Y%m%d_%H%M")"
```

This will start both the benchmark and a web dashboard at http://localhost:8080 for real-time monitoring.

**Alternative: Using the shell script:**

```bash
./utils/progress_check/run_with_monitor.sh "logs/gaia-validation-claude37sonnet/$(date +"%Y%m%d_%H%M")"
```

**Checking progress:**
```bash
uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
```

**Start monitoring for existing logs:**
```bash
./utils/progress_check/run_with_monitor.sh --monitor-only $PATH_TO_LOG
```

**Resume running if interrupted:**
```bash
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation_claude37sonnet \
  output_dir="$PATH_TO_LOG"
```

## Visualization (gaia-val)
```bash
uv run utils/progress_check/generate_gaia_report.py <task_id>
```

## Other Benchmark Datasets
Prepare dataset:
```bash
uv run prepare-benchmark get futurex # etc
```

Run benchmark
```bash
uv run main.py common-benchmark --config_file_name=agent_finsearchcomp_claude37sonnet benchmark=finsearchcomp output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

Check progress while running
```bash
uv run utils/progress_check/check_finsearchcomp_progress.py $PATH_TO_LOG
```

Resume interrupted evaluation
```bash
uv run main.py common-benchmark --config_file_name=agent_finsearchcomp_claude37sonnet benchmark=finsearchcomp output_dir="$PATH_TO_LOG"
```

## Run/resume GAIA-val with web monitor
```bash
uv run main.py run-gaia-with-monitor \
--config_file_name=agent_gaia-validation_claude37sonnet \
--output_dir="$PATH_TO_LOG"
```

related files:
- `main.py`
- `run_gaia_with_monitor.py`
- `utils/progress_check/generate_gaia_report.py`
- `utils/progress_check/gaia_web_monitor.py`

