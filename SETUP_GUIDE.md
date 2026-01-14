# 环境配置指南

## 已完成的配置

✅ 已安装 `uv` 包管理器（版本 0.9.25）  
✅ 已安装 Python 3.12.12  
✅ 已创建虚拟环境（位于 `/tmp/miroflow-venv`）  
✅ 已安装所有项目依赖（137 个包）

## 运行方式

### 方式 1：使用便捷脚本（推荐）

```bash
cd /mnt/data/workspace/miroflow-private
./run_test.sh
```

### 方式 2：使用 uv run 命令

```bash
cd /mnt/data/workspace/miroflow-private
export PATH="$HOME/.local/bin:$PATH"
export UV_PROJECT_ENVIRONMENT=/tmp/miroflow-venv
uv run test_single_task.py
```

### 方式 3：在新的 shell 会话中

如果你打开了新的终端，需要先设置环境变量：

```bash
source /mnt/data/workspace/miroflow-private/.envrc
cd /mnt/data/workspace/miroflow-private
uv run test_single_task.py
```

## 注意事项

1. **虚拟环境位置**：由于 `/mnt/data` 文件系统不支持符号链接，虚拟环境被创建在 `/tmp/miroflow-venv`。这是一个临时目录，系统重启后可能会被清除。

2. **重启后重新配置**：如果系统重启，需要重新创建虚拟环境：
   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   cd /tmp
   uv venv --python 3.12 miroflow-venv
   cd /mnt/data/workspace/miroflow-private
   export UV_PROJECT_ENVIRONMENT=/tmp/miroflow-venv
   uv sync
   ```

3. **环境变量**：脚本会从 `.env` 文件加载环境变量。如果需要配置 API 密钥等，请创建 `.env` 文件。

## 依赖包

项目已安装以下主要依赖：
- anthropic (0.60.0) - Anthropic API 客户端
- openai (1.78.1) - OpenAI API 客户端
- google-genai (1.28.0) - Google Gemini API 客户端
- e2b-code-interpreter (1.5.2) - 代码解释器
- fastmcp (2.10.6) - MCP 服务器
- hydra-core (1.3.2) - 配置管理
- pandas (2.3.1) - 数据处理
- openpyxl (3.1.5) - Excel 文件处理

以及其他 130+ 个依赖包。

## 故障排除

如果遇到 "uv: 未找到命令" 错误：
```bash
export PATH="$HOME/.local/bin:$PATH"
```

如果遇到虚拟环境错误：
```bash
cd /tmp
rm -rf miroflow-venv
uv venv --python 3.12 miroflow-venv
cd /mnt/data/workspace/miroflow-private
export UV_PROJECT_ENVIRONMENT=/tmp/miroflow-venv
uv sync
```

