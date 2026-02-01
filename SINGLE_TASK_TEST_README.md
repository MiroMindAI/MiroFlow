# 单任务测试指南

## 快速开始

### 方法1: 使用Shell脚本（推荐）

```bash
# 测试第一个任务（索引0）
./scripts/test_single_task.sh 0

# 测试第5个任务（索引4）
./scripts/test_single_task.sh 4

# 通过任务ID测试
./scripts/test_single_task.sh --task-id "7d4a7d1d-cac6-44a8-96e8-ea9584a70825"

# 测试自定义问题
./scripts/test_single_task.sh --task-question "What is 2+2?" --ground-truth "4"
```

### 方法2: 直接使用Python脚本

```bash
# 通过索引测试
uv run python test_single_task.py \
    --config-path config/standard_gaia-validation-text-103_kimi_k25.yaml \
    --task-index 0

# 通过任务ID测试
uv run python test_single_task.py \
    --config-path config/standard_gaia-validation-text-103_kimi_k25.yaml \
    --task-id "7d4a7d1d-cac6-44a8-96e8-ea9584a70825"

# 测试自定义问题
uv run python test_single_task.py \
    --config-path config/standard_gaia-validation-text-103_kimi_k25.yaml \
    --task-question "According to Wikipedia, who invented the telephone?" \
    --ground-truth "Alexander Graham Bell"
```

## 参数说明

### Shell脚本参数

```bash
./scripts/test_single_task.sh [OPTIONS] [TASK_INDEX]
```

**位置参数:**
- `TASK_INDEX`: 任务索引（0-based），例如 `0` 表示第一个任务

**选项参数:**
- `--config <path>`: 配置文件路径（默认: `config/standard_gaia-validation-text-103_kimi_k25.yaml`）
- `--output-dir <path>`: 输出目录（默认: `logs/single_task_tests`）
- `--task-id <id>`: 通过任务ID测试
- `--task-question <question>`: 自定义问题
- `--ground-truth <answer>`: 标准答案（可选）

### Python脚本参数

```bash
python test_single_task.py [OPTIONS]
```

**必需参数（任选其一）:**
- `--task-index <index>`: 任务索引（0-based）
- `--task-id <id>`: 任务ID
- `--task-question <question>`: 自定义问题

**其他参数:**
- `--config-path <path>`: 配置文件路径（必需）
- `--output-dir <path>`: 输出目录（默认: `logs/single_task_tests`）
- `--ground-truth <answer>`: 标准答案（可选）

## 使用示例

### 示例1: 快速测试第一个任务

```bash
./scripts/test_single_task.sh 0
```

输出:
```
==================================================
Single Task Test Runner
==================================================
Configuration:
  Config file: config/standard_gaia-validation-text-103_kimi_k25.yaml
  Output dir:  logs/single_task_tests

Running test...

================================================================================
Testing Single Task
================================================================================
Task ID: 7d4a7d1d-cac6-44a8-96e8-ea9584a70825
Question: Who nominated the only Featured Article on English Wikipedia about a dinosaur that was promoted in November 2016?
Ground Truth: FunkMonk
================================================================================

Initializing agent...
Agent initialized: IterativeAgentWithToolAndRollback

Running task...

================================================================================
RESULTS
================================================================================
Status: success
Final Answer: FunkMonk
Ground Truth: FunkMonk
Correct: True

Output directory: logs/single_task_tests/single_task_7d4a7d1d_20260130_213000
Task log: logs/single_task_tests/single_task_7d4a7d1d_20260130_213000/task_7d4a7d1d-cac6-44a8-96e8-ea9584a70825_attempt_1_retry_0.json
================================================================================

✓ Test completed successfully!
```

### 示例2: 通过任务ID测试特定任务

```bash
./scripts/test_single_task.sh --task-id "2dfc4c37-fec1-4518-84a7-10095d30ad75"
```

### 示例3: 测试自定义问题

```bash
./scripts/test_single_task.sh \
    --task-question "What is the capital of France?" \
    --ground-truth "Paris"
```

### 示例4: 使用不同的配置

```bash
./scripts/test_single_task.sh \
    --config config/standard_gaia-validation-text-165_mirothinker.yaml \
    --task-index 0
```

## 查看测试结果

测试完成后，结果会保存在输出目录中：

```bash
# 查看最新的测试日志
ls -lt logs/single_task_tests/ | head -5

# 查看特定任务的详细日志
cat logs/single_task_tests/single_task_<task_id>_<timestamp>/task_*.json | jq .
```

## 常见问题

### Q: 如何查看有哪些任务可以测试？

A: 可以查看benchmark文件：

```bash
# 查看GAIA验证集任务列表
cat benchmarks/gaia-validation-text-only.jsonl | jq -r '.task_id'

# 查看任务数量
wc -l benchmarks/gaia-validation-text-only.jsonl
```

### Q: 测试失败了怎么办？

A: 查看详细的日志文件：

```bash
# 查看任务执行日志
cat logs/single_task_tests/single_task_*/task_*.json | jq .

# 查看错误信息
cat logs/single_task_tests/single_task_*/task_*.json | jq '.task_meta.error'
```

### Q: 如何测试失败的任务？

A: 从之前的运行日志中找到失败的任务ID，然后使用 `--task-id` 参数重新测试：

```bash
# 1. 找到失败的任务ID
cat logs/gaia-validation-text-only/*/run_1/task_*.json | jq -r 'select(.task_meta.status=="failed") | .task_meta.task_id'

# 2. 重新测试该任务
./scripts/test_single_task.sh --task-id "<失败的任务ID>"
```

## 调试技巧

### 启用详细日志

修改配置文件中的日志级别：

```yaml
# config/standard_gaia-validation-text-103_kimi_k25.yaml
benchmark:
  execution:
    log_level: DEBUG  # 修改为DEBUG以获得更详细的日志
```

### 实时查看执行过程

使用 `tail -f` 实时查看日志：

```bash
# 在另一个终端中运行
tail -f logs/single_task_tests/*/task_*.json
```

## 配置说明

确保配置文件中设置了正确的参数：

```yaml
# config/standard_gaia-validation-text-103_kimi_k25.yaml
provider_class: "OpenRouterClient"
model_name: "moonshotai/kimi-k2.5"  # 注意是 moonshotai，不是 moonshot
use_tool_calls: false  # 使用文本模式，不使用tool_calls
```

## 性能优化

- **单任务测试**: 使用本脚本快速迭代和调试
- **批量测试**: 使用 `scripts/standard_gaia-validation-text-103_kimi_k25_8runs.sh` 进行完整评估
- **并发控制**: 单任务测试总是使用 `max_concurrent=1`
