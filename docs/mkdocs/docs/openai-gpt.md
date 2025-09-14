# OpenAI GPT Models

## What This Is
OpenAI's latest models including GPT-4o and O3 reasoning models with strong coding, vision, and reasoning capabilities.

## Client Used
`GPTOpenAIClient`

## Environment Setup
```bash
export OPENAI_API_KEY="your-openai-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # optional
```

## Configuration
```yaml
main_agent:
  llm: 
    provider_class: "GPTOpenAIClient"
    model_name: "gpt-4o"  # or o3, etc.
    openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
    openai_base_url: "${oc.env:OPENAI_BASE_URL,https://api.openai.com/v1}"
    ...
```


## Usage
```bash
# Create custom OpenAI config
uv run main.py trace --config_file_name=your_config_file \
    --task="Your task" --task_file_name="data/file.txt"
```




---
**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI