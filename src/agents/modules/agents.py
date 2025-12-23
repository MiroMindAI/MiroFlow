# src/core/agent_runner.py

from __future__ import annotations

import asyncio
import os
import json
from dataclasses import dataclass
import uuid
from omegaconf import DictConfig
from src.logging.logger import bootstrap_logger
from typing import Callable, Awaitable

from src.logging.task_tracer import get_tracer
from src.tool.manager import ToolManager

#foundation
from src.agents.registry import build_agent, register_module
from src.agents.base_module import BaseAgentModule, AgentContextDict
from src.agents.modules.sequential import SequentialAgentModule

AgentCaller = Callable[[str, dict], Awaitable[str]]

@register_module("IterativeAgentWithTool")
class IterativeAgentWithTool(BaseAgentModule):
    def __init__(self, cfg: DictConfig):
        super().__init__(cfg = cfg)
        
        self.input_processor = SequentialAgentModule(
            modules = [self.create_sub_module(module_cfg) for module_cfg in self.cfg.get('input_processor', [])] 
        )
        self.output_processor = SequentialAgentModule(
            modules = [self.create_sub_module(module_cfg) for module_cfg in self.cfg.get('output_processor', [])] 
        )

    # ---------------------------- entrypoint ----------------------------
    async def run_internal(self, ctx: AgentContextDict) -> AgentContextDict:
        tracer = get_tracer()
        tracer.save_agent_states(self.name, states = {})

        if 'message_history' not in ctx or ctx.get('message_history', None) is None:
            input_processor_output = await self.input_processor.run(AgentContextDict(
                **ctx, 
                mcp_server_definitions = self.mcp_server_definitions
            ))
            initial_user_message = input_processor_output.get("initial_user_message", None)
            system_prompt = input_processor_output.get("system_prompt", None)
            if system_prompt is None or initial_user_message is None:
                raise ValueError("system_prompt and initial_user_message are required")
            message_history = [{"role": "user", "content": initial_user_message}]
        else:
            message_history = ctx['message_history']
            input_processor_output = None
        #tracer.save_agent_states(self.name, states = {'input_processor_output': input_processor_output})

        turn_count = 0 #TODO turn_count calc from message_history, or set it as a state variable
        max_turns = self.cfg.get("max_turns", -1) 
        task_failed = False

        while max_turns == -1 or turn_count < max_turns:
            turn_count += 1

            #------------------------LLM call-----------------------

            llm_output = await self.llm_client.create_message(
                system_prompt = system_prompt, 
                message_history = message_history,
                tool_definitions = self.tool_definitions
            )
            if llm_output.is_invalid:
                task_failed = True
                break
            message_history.append(llm_output.assistant_message)
            tracer.save_agent_states(self.name, states = {'message_history': message_history})

            #------------------------Tool calls-----------------------
            tool_and_sub_agent_calls = self.llm_client.extract_tool_calls_info(llm_output.raw_response, llm_output.response_text)[0]
            if len(tool_and_sub_agent_calls) == 0:
                break
            else:
                tool_calls = [call for call in tool_and_sub_agent_calls if 'agent-worker' not in call['server_name']]
                sub_agent_calls = [call for call in tool_and_sub_agent_calls if 'agent-worker' in call['server_name']]

                tool_results, tool_calls_exceeded = await self.tool_manager.execute_tool_calls_batch(tool_calls)
                sub_agent_results = await self.run_sub_agents_as_mcp_tools(sub_agent_calls)
                all_call_results = self.tool_manager.format_tool_results(tool_results + sub_agent_results)
            
            message_history = self.llm_client.update_message_history(
                message_history, all_call_results, tool_calls_exceeded 
            ) #TODO modify each client; return a single message
            tracer.save_agent_states(self.name, states = {'message_history': message_history})
        
        
        output_processor_result = await self.output_processor.run(AgentContextDict(
            **ctx,
            message_history = message_history,
            task_failed = task_failed
        ))
        tracer.save_agent_states(self.name, states = {
            'message_history': message_history,
            'summary': output_processor_result.get("summary", None)
        })
        return AgentContextDict(
            message_history = message_history, 
            summary = output_processor_result.get("summary", None),
            final_boxed_answer = output_processor_result.get("final_boxed_answer", None)
        )