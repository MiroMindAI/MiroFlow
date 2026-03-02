# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import importlib

from miroflow.logging.task_tracer import get_tracer

logger = get_tracer()


def _load_agent_prompt_class(prompt_class_name: str):
    # Dynamically import the class from the config.agent_prompts module
    if not isinstance(prompt_class_name, str) or not prompt_class_name.isidentifier():
        raise ValueError(f"Invalid prompt class name: {prompt_class_name}")

    try:
        # Import the module dynamically
        agent_prompts_module = importlib.import_module("config.agent_prompts")
        # Get the class from the module
        PromptClass = getattr(agent_prompts_module, prompt_class_name)
    except (ModuleNotFoundError, AttributeError) as e:
        raise ImportError(
            f"Could not import class '{prompt_class_name}' from 'config.agent_prompts': {e}"
        )
    return PromptClass()


# def expose_sub_agents_as_tools(sub_agents_cfg: DictConfig):
#     """Expose sub-agents as tools"""
#     sub_agents_server_params = []
#     for sub_agent in sub_agents_cfg.keys():
#         if not sub_agent.startswith("agent-"):
#             raise ValueError(
#                 f"Sub-agent name must start with 'agent-': {sub_agent}. Please check the sub-agent name in the agent's config file."
#             )
#         try:
#             sub_agent_prompt_instance = _load_agent_prompt_class(
#                 sub_agents_cfg[sub_agent].prompt_class
#             )
#             sub_agent_tool_definition = sub_agent_prompt_instance.expose_agent_as_tool(
#                 subagent_name=sub_agent
#             )
#             sub_agents_server_params.append(sub_agent_tool_definition)
#         except Exception as e:
#             raise ValueError(f"Failed to expose sub-agent {sub_agent} as a tool: {e}")
#     return sub_agents_server_params


def expose_sub_agents_as_tools(sub_agent_names):
    """Expose sub-agents as tools"""
    sub_agents_server_params = []
    for sub_agent_name in sub_agent_names:
        # if not sub_agent_name.startswith("agent-"):
        #     raise ValueError(
        #         f"Sub-agent name must start with 'agent-': {sub_agent}. Please check the sub-agent name in the agent's config file."
        #     )
        try:
            sub_agent_tool_definition = dict(
                name=sub_agent_name,
                tools=[
                    dict(
                        name="execute_subtask",
                        description="This tool is an agent that performs various subtasks to collect information and execute specific actions. It can access the internet, read files, program, and process multimodal content, but is not specialized in complex reasoning or logical thinking. The tool returns processed summary reports rather than raw information - it analyzes, synthesizes, and presents findings in a structured format. The subtask should be clearly defined, include relevant background, and focus on a single, well-scoped objective. It does not perform vague or speculative subtasks. \nArgs: \n\tsubtask: the subtask to be performed. \nReturns: \n\tthe processed summary report of the subtask. ",
                        schema={
                            "type": "object",
                            "properties": {
                                "subtask": {"title": "Subtask", "type": "string"}
                            },
                            "required": ["subtask"],
                            "title": "execute_subtaskArguments",
                        },
                    )
                ],
            )
            sub_agents_server_params.append(sub_agent_tool_definition)
        except Exception as e:
            raise ValueError(
                f"Failed to expose sub-agent {sub_agent_name} as a tool: {e}"
            )
    return sub_agents_server_params


def format_tool_result(tool_call_execution_result):
    """
    Format tool execution results to be fed back to LLM as user messages.
    Only includes necessary information (results or errors).
    """
    server_name = tool_call_execution_result["server_name"]
    tool_name = tool_call_execution_result["tool_name"]

    if "error" in tool_call_execution_result:
        # Provide concise error information to LLM
        content = f"Tool call to {tool_name} on {server_name} failed. Error: {tool_call_execution_result['error']}"
    elif "result" in tool_call_execution_result:
        # Provide tool's original output results
        content = tool_call_execution_result["result"]
        # Can consider truncating overly long results
        max_len = 100_000  # 100k chars = 25k tokens
        if len(content) > max_len:
            content = content[:max_len] + "\n... [Result truncated]"
    else:
        content = f"Tool call to {tool_name} on {server_name} completed, but produced no specific output or result."

    # Return format suitable as user message content
    # return [{"type": "text", "text": content}]
    return {"type": "text", "text": content}
