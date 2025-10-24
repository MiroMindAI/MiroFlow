## Git 管理
- 开源项目的工作流一般都是 fork + 提PR 
- 一个分支本质上是代码历史中指向某个commit的指针
- feature/monitor branch: 跑benchmark的时候监控中间过程

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

**Checking progress:**
```bash
uv run utils/progress_check/check_gaia_progress.py $PATH_TO_LOG
```

**Resume running if interrupted:**
```bash
uv run main.py common-benchmark \
  --config_file_name=agent_gaia-validation_claude37sonnet.yaml \
  output_dir="$PATH_TO_LOG"
```


## Other Benchmark Datasets