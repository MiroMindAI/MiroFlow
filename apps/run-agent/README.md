# Major Update on 08/20 项目更新说明：原MiroFlow Bug修复

**Bug修复：**
1. `OPENROUTER`相关环境变量未在tool_utils中导入到reasoning工具（开源repo已同步修复）
2. ctrl+c有时无法终止任务后台运行、在`common_benchmark.py`中新增`signal_handler`（开源repo已同步修复）
3. HF下载后文件路径加载丢失后缀、去除path的resolve方法（开源repo已同步修复）
4. log实时更新的json格式有问题（开源repo已同步修复）
5. Python Server修改`DEFAULT_TEMPLATE_ID`（开源repo已同步修复）
6. Hydra config未保存到工作目录、更改`config.yaml`配置和`main.py`启动入口（开源repo已同步修复）
7. `create_message`的retry装饰应当为 retry_if_**not**_exception_type(ContextLimitError)（开源repo没有问题）
8. 将`llm_as_judge_result`改为`judge_result`

# Major Update on 08/20 项目更新说明：功能变更

本文档详细说明了所有的功能性变更，共涉及**53个文件**。

## 文件分类统计

| 文件类别 | 数量 | 具体说明 |
|---------|------|----------|
| **配置文件** | **29个** | • Agent配置(14个): claude/deepseek/qwen3/kimi/seed等组合<br>• LLM配置(13个): 各种模型参数配置<br>• Benchmark配置(2个): browsecomp-zh, xbench-ds |
| **Python代码** | **10个** | • 核心框架(6个): orchestrator, pipeline等<br>• 评估系统(2个): common_benchmark, eval_utils<br>• LLM客户端(2个): provider_client_base, anthropic_openrouter<br>• 搜索工具(1个): searching_mcp_server |
| **Shell脚本** | **8个** | • 并行评估脚本: gaia-test/validation, hle, browsecomp, xbench-ds等 |
| **工具函数** | **4个** | • util_aggregate_results_xlsx.py: Excel结果聚合<br>• util_llm_parallel_thinking.py: 并行思考<br>• util_llm_simple_voting.py: 投票机制<br>• util_statistics_hle_text_only.py: HLE统计 |
| **依赖管理** | **2个** | • pyproject.toml: 添加pandas和openpyxl<br>• uv.lock: 依赖锁定文件 |
| **总计** | **53个** | 配置文件占比54.7%，代码文件占比45.3% |

## 目录
- [依赖更新](#依赖更新)
- [核心功能改进](#核心功能改进)
- [新增配置文件](#新增配置文件)
- [评估系统增强](#评估系统增强)
- [工具函数新增](#工具函数新增)
- [搜索工具优化](#搜索工具优化)

---

## 依赖更新

### 1. apps/run-agent/pyproject.toml & uv.lock
**变更内容：**
- 新增依赖：`openpyxl>=3.1.5` 和 `pandas>=2.3.0`
- 用于支持Excel文件处理和数据分析功能

**影响：** 增强了数据处理能力，特别是对评估结果的Excel导出支持，支持新增的分析工具（`util`）

---

## 核心功能改进

### 2. common_benchmark.py
**变更内容：**
- 修改JSON输出时添加 `ensure_ascii=False` 参数
- 确保中文等非ASCII字符能正确保存

**代码变更：**
```python
# 原代码
json.dumps(asdict(result))
# 新代码
json.dumps(asdict(result), ensure_ascii=False)
```

**影响：** 改善了对中文benchmark（如xbench-ds、browsecomp-zh）的支持

### 3. eval_utils.py 
**主要改进：**
1. **新增XBench评估支持**
   - 添加了 `verify_answer_llm_xbench()` 函数，支持中文基准测试评估
   - 使用o3作为裁判模型（可配置为Gemini 2.0 Flash）
   - 支持中文prompt和结构化输出

2. **错误处理增强**
   - 所有评估函数添加了 `@retry` 装饰器，使用tenacity实现重试机制
   - 重试策略：指数退避，最多5次尝试

3. **异常处理统一化**
   - 将原来的简单try-catch改为更严格的异常处理
   - 失败时抛出具体异常而不是返回NOT_ATTEMPED默认值

**新增的XBench评估prompt模板：**
```python
XBENCH_LLM_JUDGE_PROMPT = """
你是一个通用人工智能助手。根据下面给出的[正确答案], 判断以下对[原问题]的[回答]的回答是否正确。
...
结论: 如果[最终答案]与上方给出的[正确答案]一致...则填写'正确'; 否则...填写'错误'。
"""
```

### 4. libs/miroflow/src/miroflow/prebuilt/orchestrator.py
**重大改进：**

1. **双LLM客户端支持**
   - 新增 `sub_agent_llm_client` 参数，允许主agent和子agent使用不同的LLM模型
   - 自动根据agent类型选择正确的LLM客户端

2. **中文上下文支持**
   - 通过环境变量 `CHINESE_CONTEXT` 控制
   - 在O3提示抽取和最终答案抽取中添加中文特定指导

3. **O3最终答案抽取增强**
   - 添加了详细的置信度评估指导（0-100分）
   - 新增支持证据和潜在不足的结构化输出
   - 支持中英文双语输出格式

4. **Context限制检查优化**
   - 注释掉了原有的context限制检查代码（已有ContextLimitError处理，去除冗余）

**中文支持示例：**
```python
if chinese_context:
    instruction += """
## 中文分析指导
如果问题涉及中文语境，请特别注意：
- 语言理解：识别可能存在的中文表达歧义...
- 文化背景：考虑可能需要中文文化背景知识...
"""
```

### 5. libs/miroflow/src/miroflow/prebuilt/pipeline.py
**变更内容：**
- 支持为主agent和子agent分别配置不同的LLM
- 从配置文件动态加载LLM配置
- 改进了资源清理逻辑

**代码改进：**
```python
# 新增主agent LLM配置加载
main_agent_llm_config = cfg.agent.get("main_agent_llm", None)
if main_agent_llm_config:
    main_agent_cfg = OmegaConf.load(f"conf/llm/{main_agent_llm_config}.yaml")
    llm_client = LLMClient(task_id=task_id, cfg=OmegaConf.create({"llm": main_agent_cfg}))

# 新增子agent LLM配置加载
sub_agent_llm_config = cfg.agent.get("sub_agent_llm", None)
```

### 6. libs/miroflow/src/miroflow/utils/io_utils.py
**重要改进：**
- 重写了 `_extract_boxed_content()` 方法
- 使用平衡括号计数算法替代正则表达式
- 正确处理任意层级的嵌套括号

**算法改进：**
```python
# 新算法：通过计数括号来处理嵌套
brace_count = 1
while content_end < len(text) and brace_count > 0:
    if char == '{':
        brace_count += 1
    elif char == '}':
        brace_count -= 1
```

### 7. libs/miroflow/src/miroflow/utils/prompt_utils.py
**全面的中文支持增强：**

1. **MCP系统prompt中文指导**
   - 子任务委托使用中文描述
   - 搜索关键词使用中文
   - 思考过程使用中文表达

2. **Agent特定prompt改进**
   - 主agent：支持reasoning工具和深度思考两种模式
   - Worker agent：添加中文内容处理指导，包括Google搜索参数设置

3. **总结prompt中文支持**
   - 所有agent类型都添加了中文总结要求

---

## 新增配置文件

### Agent配置文件（18个新文件）
位置：`libs/miroflow/src/miroflow/prebuilt/config/agent/`

**双模型配置系列：**
- `claude03_claude_dual.yaml` - Claude 3.7 Sonnet (temp=0.3) 主从配置
- `claude05_claude_dual.yaml` - Claude 3.7 Sonnet (temp=0.5) 主从配置  
- `claude07_claude_dual.yaml` - Claude 3.7 Sonnet (temp=0.7) 主从配置
- `deepseek_claude_dual.yaml` - DeepSeek R1主 + Claude 3.7从
- `deepseek_deepseek_dual.yaml` - DeepSeek全栈配置
- `deepseek_kimi_dual.yaml` - DeepSeek主 + Kimi K2从
- `deepseek_qwen3_dual.yaml` - DeepSeek主 + Qwen3从
- `deepseek_qwen3flash_dual.yaml` - DeepSeek主 + Qwen3 Flash从
- `gptoss_gptoss_dual.yaml` - GPT-OSS 120B全栈配置
- `kimi_claude_dual.yaml` - Kimi K2主 + Claude从
- `qwen3_claude_dual.yaml` - Qwen3主 + Claude从
- `seed_claude_dual.yaml` - Seed 1.6主 + Claude从

**特殊配置：**
- `deepseek_nohint_claude_dual.yaml` - 禁用O3提示
- `deepseek_nohintreason_claude_dual.yaml` - 禁用O3提示和推理工具

### LLM配置文件（13个新文件）
位置：`libs/miroflow/src/miroflow/prebuilt/config/llm/`

**新增模型配置：**
1. **Claude系列**
   - `claude-3.7-sonnet_temp03.yaml` (temperature=0.3)
   - `claude-3.7-sonnet_temp05.yaml` (temperature=0.5)
   - `claude-3.7-sonnet_temp07.yaml` (temperature=0.7)
   - `claude-4-sonnet.yaml` - Claude 4配置

2. **DeepSeek系列**
   - `deepseek-r1-0528.yaml` - DeepSeek R1模型
   - `deepseek-v3.yaml` - DeepSeek V3 (火山方舟)

3. **其他模型**
   - `gemini-2-5-pro.yaml` - Gemini 2.5 Pro
   - `gpt-oss-120b.yaml` - GPT-OSS 120B
   - `kimi-k2.yaml` - Kimi K2 (火山方舟)
   - `qwen3-235b-thinking.yaml` - Qwen3 235B思考模型（火山云自部署）
   - `qwen3-coder.yaml` - Qwen3 Coder 480B（火山云自部署）
   - `qwen3-coder-flash.yaml` - Qwen3 Coder 30B Flash（火山云自部署）
   - `seed-1-6-thinking.yaml` - Seed 1.6思考模型 (火山方舟)

### Benchmark配置文件（2个新文件）
位置：`libs/miroflow/src/miroflow/prebuilt/config/benchmark/`
- `browsecomp-zh.yaml` - 中文浏览理解基准测试
- `xbench-ds.yaml` - XBench深度搜索基准测试

---

## 评估系统增强

### 8个新运行脚本
位置：`apps/run-agent/scripts/main-worker-dual/`

**新增的并行评估脚本：**
- `run_evaluate_multiple_runs_browsecomp-zh.sh` - 中文浏览理解评估
- `run_evaluate_multiple_runs_browsecomp.sh` - 英文浏览理解评估
- `run_evaluate_multiple_runs_gaia-test.sh` - GAIA测试集评估
- `run_evaluate_multiple_runs_gaia-validation.sh` - GAIA验证集评估
- `run_evaluate_multiple_runs_noansbox_gaia-validation.sh` -（无Google答案框）GAIA验证集评估
- `run_evaluate_multiple_runs_hle.sh` - HLE基准评估
- `run_evaluate_multiple_runs_nohintreason_hle.sh` - （无O3提示和推理工具）HLE基准评估
- `run_evaluate_multiple_runs_xbench-ds.sh` - XBench深度搜索评估

**脚本特点：**
- 支持并行运行多次实验
- 自动检测中文基准并设置 `CHINESE_CONTEXT=true`
- 支持配置环境变量控制Google搜索结果过滤
- 自动计算平均分数

---

## 工具函数新增

### util_aggregate_results_xlsx.py (416行)
**功能：** 将多次运行的基准测试结果聚合到Excel文件

**主要特性：**
- 支持多run结果合并
- 条件格式化（正确答案灰色，错误答案深红色）
- 自动计算准确率统计
- 保持run_1的任务顺序
- 支持中文内容

### util_llm_parallel_thinking.py (567行)
**功能：** 使用LLM进行并行思考和答案选择

**核心功能：**
1. **多答案聚合**
   - 从多个agent运行中提取答案
   - 使用O3模型进行最佳答案选择

2. **基准特定prompt**
   - GAIA基准：英文评估，等价性规则
   - XBench基准：中文评估，语义一致性判断

3. **并发处理**
   - 支持25个并发API请求
   - 实时进度显示和成本计算

4. **成本追踪**
   - O3定价：输入$2/1M tokens，缓存$0.5/1M，输出$8/1M

### util_llm_simple_voting.py (444行)
**功能：** 简单投票机制选择最佳答案

**实现方式：**
- 答案归一化和等价性判断
- 多数投票选择
- 支持数值、文本、列表类型答案
- 特殊规则处理（长列表、百分比等）

### util_statistics_hle_text_only.py (88行)
**功能：** HLE纯文本任务统计分析

**分析内容：**
- 任务类型分布
- 答案格式统计
- 文本长度分析

---

## 搜索工具优化

### libs/miroflow-tool/src/miroflow/tool/mcp_servers/searching_mcp_server.py

**新增功能：**

1. **Google搜索结果过滤**
   - 通过环境变量控制：
     - `REMOVE_SNIPPETS` - 移除Google摘要
     - `REMOVE_KNOWLEDGE_GRAPH` - 移除Google知识图谱
     - `REMOVE_ANSWER_BOX` - 移除Google答案框

2. **新增搜索参数**
   - `gl` - 国家上下文（如'cn'中国，'us'美国）
   - `hl` - 界面语言（如'zh'中文，'en'英文）

3. **过滤器实现**
```python
def filter_google_search_result(result_content: str) -> str:
    """根据环境变量过滤搜索结果"""
    # 移除知识图谱
    if REMOVE_KNOWLEDGE_GRAPH and "knowledgeGraph" in data:
        del data["knowledgeGraph"]
    # 移除答案框
    if REMOVE_ANSWER_BOX and "answerBox" in data:
        del data["answerBox"]
    # 移除摘要
    if REMOVE_SNIPPETS:
        for item in data["organic"]:
            if "snippet" in item:
                del item["snippet"]
```

---

## 其他改进

### LLM Provider客户端改进
**文件：** `libs/miroflow/src/miroflow/llm/provider_client_base.py` 和 `libs/miroflow/src/miroflow/llm/providers/claude_openrouter_client.py`

**改进内容：**
1. 支持 `repetition_penalty` 参数
2. 改进OpenRouter配置处理
3. 增强context限制错误检测
4. 支持通过extra_body传递top_k和min_p参数

### 相应配置增强
**文件：** `libs/miroflow/src/miroflow/prebuilt/config/config.yaml`和`libs/miroflow/src/miroflow/utils/tool_utils.py`

**新增部分环境变量传递：**
```python
"REMOVE_SNIPPETS": os.environ.get("REMOVE_SNIPPETS", "false"),
"REMOVE_KNOWLEDGE_GRAPH": os.environ.get("REMOVE_KNOWLEDGE_GRAPH", "false"),
"REMOVE_ANSWER_BOX": os.environ.get("REMOVE_ANSWER_BOX", "false"),
```
等。

---

## 总结

本次功能更新主要聚焦于：

1. **多语言支持增强** - 全面支持中文基准测试和中文语境处理
2. **评估系统升级** - 新增XBench支持，改进评估鲁棒性
3. **灵活的模型配置** - 支持主从agent使用不同LLM模型
4. **评测链完善** - 新增多个实用utils工具函数，支持voting & selecting
5. **搜索优化** - 可配置的搜索结果过滤

这些改进显著提升了系统的灵活性、可靠性和对中文任务的支持能力。