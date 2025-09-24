# MiroThinker

[MiroThinker](https://github.com/MiroMindAI/MiroThinker) (4B/7B/14B/32B) is our suite of open-source agentic models, designed to work seamlessly with the MiroFlow framework. Our models are specifically built to handle **complex, multi-tool tasks**, leveraging the reproducible and robust foundation that MiroFlow provides.

By combining MiroFlow's reliable orchestration with MiroThinker's advanced reasoning capabilities, we offer a powerful, end-to-end solution for building high-performing, reproducible AI agents.

These models are a direct result of our extensive data collection efforts, utilizing MiroFlow to generate high-quality, post-training agent trace data. This unique approach enables MiroThinker to excel in planning, executing, and reasoning through complex multi-step tasks.

---

## Deploying MiroThinker-32B with MiroFlow

This guide explains how to deploy the MiroThinker-32B-DPO-v0.2 model from Hugging Face and integrate it with MiroFlow.

### Prerequisites

- SGLang installed
- Sufficient GPU memory for the model
- MiroFlow repository set up

### Step 1: Deploy Model with SGLang

Deploy the MiroThinker-32B model using SGLang:

```bash title="SGLang Server Deployment"
python3 -m sglang.launch_server \
    --model-path miromind-ai/MiroThinker-32B-DPO-v0.2 \
    --tp 8 \
    --dp 1 \
    --host 0.0.0.0 \
    --port 61005 \
    --trust-remote-code \
    --chat-template qwen3_nonthinking.jinja
```

!!! warning "Important Notes"
    - Adjust the `--tp` (tensor parallelism) parameter to match your number of GPUs
    - Download the chat template from: [qwen3_nonthinking.jinja](https://qwen.readthedocs.io/zh-cn/latest/_downloads/c101120b5bebcc2f12ec504fc93a965e/qwen3_nonthinking.jinja)
    - Ensure the port you used (in this case 61005) is available on your system

### Step 2: Configure MiroFlow

Once the SGLang server is running, configure MiroFlow by adding the following to your `.env` file:

```bash title="Environment Configuration"
OAI_MIROTHINKER_API_KEY="dummy_key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"
```

!!! note "Configuration Notes"
    - If your model requires authentication, replace `dummy_key` with your actual API key
    - Replace `localhost` with the appropriate hostname if deploying on a remote server

### Step 3: Test the Integration

Test your setup with the following command:

```bash title="Test Command"
uv run main.py trace --config_file_name=agent_mirothinker \
    --task="What is the first country listed in the XLSX file that have names starting with Co?" \
    --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

This command will:
- Use the `agent_mirothinker` configuration with the dedicated MiroThinkerSGLangClient
- Process the specified Excel file
- Query the model to find countries starting with "Co"

### Configuration Details

The `./config/agent_mirothinker.yaml` configuration file uses:

- `provider_class: "MiroThinkerSGLangClient"` - A dedicated client for MiroThinker models deployed with SGLang
- Model path and generation parameters (temperature, top_p, max_tokens, etc.)
- Environment variables for API endpoint configuration

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Xalp @ MiroMind AI