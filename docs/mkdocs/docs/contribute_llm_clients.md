# Contributing New LLM Clients

Add support for new LLM providers to MiroFlow by creating a provider class that integrates with the existing client infrastructure.

## Client Structure

Each LLM client inherits from `LLMProviderClientBase` and implements 4 required methods:

- `_create_client()` - Initialize API client
- `_create_message()` - Make API calls  
- `process_llm_response()` - Handle responses
- `extract_tool_calls_info()` - Parse tool calls

---

## Implementation Steps

### Step 1: Create Provider File

Create `src/llm/providers/your_provider_client.py`:

```python title="Provider Implementation"
import dataclasses
from src.llm.provider_client_base import LLMProviderClientBase

@dataclasses.dataclass
class YourProviderClient(LLMProviderClientBase):
    def _create_client(self, config):
        # Initialize your API client
        pass

    async def _create_message(self, system_prompt, messages, tools_definitions, keep_tool_result=-1):
        # Make API call
        pass

    def process_llm_response(self, llm_response, message_history, agent_type="main"):
        # Extract response text, return (text, should_exit)
        pass

    def extract_tool_calls_info(self, llm_response, assistant_response_text):
        # Parse tool calls, return (tool_calls, tool_names)
        pass
```

### Step 2: Create Configuration

```yaml title="Agent Configuration"
main_agent:
  llm: 
    provider_class: "YourProviderClient"
    model_name: "your-model"
    your_api_key: "${oc.env:YOUR_API_KEY,???}"
    your_base_url: "${oc.env:YOUR_BASE_URL,https://api.yourprovider.com/v1}"
```

### Step 3: Set Environment Variables

```bash title="Environment Setup"
export YOUR_API_KEY="your-key"
export YOUR_BASE_URL="https://api.yourprovider.com/v1"  # optional if using default
```

## Examples

See existing providers in `src/llm/providers/`:

- `ClaudeAnthropicClient` - Direct API
- `ClaudeOpenRouterClient` - Proxy API  
- `GPTOpenAIClient` - OpenAI API

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI