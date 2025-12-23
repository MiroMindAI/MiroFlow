from omegaconf import DictConfig

from src.agents.base_module import BaseAgentModule
from src.agents.registry import register_module
from src.utils.prompt_manager import PromptTemplateReader
import os
from src.utils.io_utils import get_file_type
import datetime
from src.utils.summary_utils import extract_hints

@register_module("InputHintGenerator")
class InputHintGenerator(BaseAgentModule):
    USE_PROPAGATE_MODULE_CONFIGS = ("llm", "prompt")
    async def run_internal(self, ctx: dict):
        prompt = self.prompt_manager.render_prompt('hint_generation_prompt', context = dict(task_description = ctx.get("task_description"), chinese_context = self.cfg.get("chinese_context",False)))
        task_hint = await self.llm_client.create_message(prompt)
        return {
            'task_hint': task_hint.response_text
        }

@register_module("InputMessageGenerator")
class InputMessageGenerator(BaseAgentModule):
    USE_PROPAGATE_MODULE_CONFIGS = ("prompt", )
    async def run_internal(self, ctx: dict):
        if ctx.get('task_file_name') is not None:
            task_file_name = ctx['task_file_name']
            task_file_type = get_file_type(task_file_name)
            file_input = dict(file_type = task_file_type, file_name = task_file_name,
            absolute_file_path = os.path.abspath(task_file_name))
        else:
            file_input = None

        initial_user_message = self.prompt_manager.render_prompt(
            prompt_name = 'initial_user_text',
            context = dict(task_description = ctx.get("task_description"), file_input = file_input, task_hint = ctx.get("task_hint", None))
        )

        system_prompt = self.prompt_manager.render_prompt(  
            prompt_name='system_prompt',
            context = dict(formatted_date = datetime.datetime.now().strftime("%Y-%m-%d"), mcp_server_definitions = ctx.get("mcp_server_definitions", None))
        )
        
        return {
            'system_prompt': system_prompt,
            'initial_user_message': initial_user_message
        }