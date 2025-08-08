# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from typing import Optional

from omegaconf import DictConfig, OmegaConf

from miroflow.logging.task_tracer import TaskTracer

from .providers.claude_anthropic_client import ClaudeAnthropicClient
from .providers.claude_newapi_client import ClaudeNewAPIClient
from .providers.claude_openrouter_client import ClaudeOpenRouterClient
from .providers.deepseek_newapi_client import DeepSeekNewAPIClient
from .providers.gpt_openai_client import GPTOpenAIClient
from .providers.gpt_openai_response_client import GPTOpenAIResponseClient
from .providers.qwen_sglang_client import QwenSGLangClient


def LLMClient(
    task_id: str, cfg: DictConfig, task_log: Optional[TaskTracer] = None, **kwargs
):
    """
    create LLMClientProvider from hydra configuration.
    """
    provider = cfg.llm.provider
    config = OmegaConf.merge(cfg, kwargs)

    assert isinstance(config, DictConfig), "expect a dict config"

    client_creators = {
        "anthropic": lambda: ClaudeAnthropicClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
        "openai": lambda: GPTOpenAIClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
        "openai_response": lambda: GPTOpenAIResponseClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
        "qwen": lambda: QwenSGLangClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
        "claude_newapi": lambda: ClaudeNewAPIClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
        "deepseek_newapi": lambda: DeepSeekNewAPIClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
        "claude_openrouter": lambda: ClaudeOpenRouterClient(
            task_id=task_id, task_log=task_log, cfg=config
        ),
    }

    factory = client_creators.get(provider)
    if not factory:
        raise ValueError(f"Unsupported provider: {provider}")

    return factory()
