# Trace Analysis Web Demo

一个交互式的Web界面，用于分析和可视化trace JSON文件。

## 功能特性

- 🔍 **交互式分析**: 直观的Web界面，可以轻松浏览和分析trace数据
- 📊 **执行流程可视化**: 清晰展示main agent和browser agent的执行流程
- 🛠️ **工具调用追踪**: 详细显示MCP工具调用的信息和参数
- 📱 **响应式设计**: 支持桌面和移动设备访问
- 💾 **文件管理**: 支持动态加载和切换不同的trace文件

## 项目结构

```
web_demo/
├── app.py              # Flask后端应用
├── trace_analyzer.py   # 核心分析逻辑
├── run.py              # 启动脚本
├── requirements.txt    # Python依赖
├── README.md          # 说明文档
├── templates/
│   └── index.html     # 主页面模板
└── static/
    ├── css/
    │   └── style.css  # 样式文件
    └── js/
        └── script.js  # 前端交互逻辑
```

## 安装和运行

### 方法1: 使用Python (推荐)

```bash
pip install -r requirements.txt
python run.py
```

启动脚本会自动检查和安装依赖，然后启动Web应用。访问`http://127.0.0.1:5000`

### 方法2: 使用uv

```bash
uv run run.py
```

## 使用方法

1. **启动应用**: 运行后在浏览器中访问 `http://127.0.0.1:5000`

2. **加载文件**: 
   - 在顶部导航栏的下拉菜单中选择要分析的trace JSON文件
   - 点击"加载"按钮加载文件

3. **查看分析结果**:
   - **左侧面板**: 显示基本信息、执行摘要和性能统计
   - **右侧面板**: 展示详细的执行流程
   - **底部面板**: 显示spans统计和步骤日志统计

4. **交互操作**:
   - 点击执行步骤可以展开/收起详细信息
   - 使用"展开所有"/"收起所有"按钮控制全部步骤
   - 点击"查看详情"按钮查看完整的消息内容

## 界面说明

### 执行流程视图

- **用户消息**: 蓝色背景，表示用户输入
- **助手消息**: 紫色背景，表示AI助手回复
- **Browser Agent**: 绿色/橙色背景，表示浏览器代理操作
- **工具调用**: 黄色背景，显示工具调用信息
- **Browser会话**: 灰色背景，显示browser agent的详细对话

### 颜色编码

- 🔵 **蓝色**: Main Agent用户消息
- 🟣 **紫色**: Main Agent助手消息
- 🟢 **绿色**: Browser Agent用户消息
- 🟠 **橙色**: Browser Agent助手消息
- 🟡 **黄色**: 工具调用
- 🟢 **绿色标签**: Browser会话标识

## 数据结构

该工具支持分析包含以下结构的JSON文件：

- `main_agent_message_history`: 主代理的对话历史
- `browser_agent_message_history_sessions`: 浏览器代理的会话历史
- `trace_data.spans`: 执行跟踪数据
- `step_logs`: 步骤日志
- `performance_summary`: 性能摘要信息

## API接口

后端提供以下API接口：

- `GET /`: 主页面
- `GET /api/list_files`: 获取可用的JSON文件列表
- `POST /api/load_trace`: 加载指定的trace文件
- `GET /api/basic_info`: 获取基本信息
- `GET /api/execution_flow`: 获取执行流程
- `GET /api/execution_summary`: 获取执行摘要
- `GET /api/performance_summary`: 获取性能摘要
- `GET /api/spans_summary`: 获取spans统计
- `GET /api/step_logs_summary`: 获取步骤日志统计

## 技术栈

- **后端**: Flask (Python)
- **前端**: HTML5, CSS3, JavaScript (ES6+)
- **UI框架**: Bootstrap 5
- **图标**: Font Awesome
- **数据处理**: JSON, 正则表达式

## 开发说明

### 添加新功能

1. **后端**: 在 `app.py` 中添加新的API端点
2. **数据分析**: 在 `trace_analyzer.py` 中添加新的分析方法
3. **前端**: 在 `script.js` 中添加相应的API调用和界面更新逻辑
4. **样式**: 在 `style.css` 中添加相应的样式定义