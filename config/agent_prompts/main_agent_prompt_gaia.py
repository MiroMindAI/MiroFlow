from config.agent_prompts.base_agent_prompt import BaseAgentPrompt
import datetime
from typing import Any


class MainAgentPrompt_GAIA(BaseAgentPrompt):
    """
    MainAgentGaiaPrompt inherits from BaseAgentPrompt and can be extended
    with main agent-specific prompt logic or configuration.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.is_main_agent = True

    def generate_system_prompt_with_mcp_tools(
        self, mcp_servers: list[Any], chinese_context: bool = False
    ) -> str:
        formatted_date = datetime.datetime.today().strftime("%Y-%m-%d")

        # Basic system prompt
        prompt = f"""In this environment you have access to a set of tools you can use to answer the user's question. 

You only have access to the tools provided below. You can only use one tool per message, and will receive the result of that tool in the user's next response. You use tools step-by-step to accomplish a given task, with each tool-use informed by the result of the previous tool-use. Today is: {formatted_date}

# Tool-Use Formatting Instructions 

Tool-use is formatted using XML-style tags. The tool-use is enclosed in <use_mcp_tool></use_mcp_tool> and each parameter is similarly enclosed within its own set of tags.

The Model Context Protocol (MCP) connects to servers that provide additional tools and resources to extend your capabilities. You can use the server's tools via the `use_mcp_tool`.

Description: 
Request to use a tool provided by a MCP server. Each MCP server can provide multiple tools with different capabilities. Tools have defined input schemas that specify required and optional parameters.

Parameters:
- server_name: (required) The name of the MCP server providing the tool
- tool_name: (required) The name of the tool to execute
- arguments: (required) A JSON object containing the tool's input parameters, following the tool's input schema, quotes within string must be properly escaped, ensure it's valid JSON

Usage:
<use_mcp_tool>
<server_name>server name here</server_name>
<tool_name>tool name here</tool_name>
<arguments>
{{
"param1": "value1",
"param2": "value2 \\"escaped string\\""
}}
</arguments>
</use_mcp_tool>

Important Notes:
- Tool-use must be placed **at the end** of your response, **top-level**, and not nested within other tags.
- Always adhere to this format for the tool use to ensure proper parsing and execution.

String and scalar parameters should be specified as is, while lists and objects should use JSON format. Note that spaces for string values are not stripped. The output is not expected to be valid XML and is parsed with regular expressions.
Here are the functions available in JSONSchema format:

"""

        # Add MCP servers section
        if mcp_servers and len(mcp_servers) > 0:
            for server in mcp_servers:
                prompt += f"## Server name: {server['name']}\n"

                if "tools" in server and len(server["tools"]) > 0:
                    for tool in server["tools"]:
                        # Skip tools that failed to load (they only have 'error' key)
                        if "error" in tool and "name" not in tool:
                            continue
                        prompt += f"### Tool name: {tool['name']}\n"
                        prompt += f"Description: {tool['description']}\n"
                        prompt += f"Input JSON schema: {tool['schema']}\n"

        # Add the full objective system prompt
        prompt += """
# General Objective

You accomplish a given task iteratively, breaking it down into clear steps and working through them methodically.
"""

        # Add Chinese-specific instructions if enabled
        if chinese_context:
            prompt += """
    ## 中文语境处理指导

    当处理中文相关的任务时：
    1. **子任务委托 (Subtask Delegation)**：向worker代理委托的子任务应使用中文描述，确保任务内容准确传达
    2. **搜索策略 (Search Strategy)**：搜索关键词应使用中文，以获取更准确的中文内容和信息
    3. **问题分析 (Question Analysis)**：对中文问题的分析和理解应保持中文语境
    4. **思考过程 (Thinking Process)**：内部分析、推理、总结等思考过程都应使用中文，保持语义表达的一致性
    5. **信息整理 (Information Organization)**：从中文资源获取的信息应保持中文原文，避免不必要的翻译
    6. **各种输出 (All Outputs)**：所有输出内容包括步骤说明、状态更新、中间结果等都应使用中文
    7. **最终答案 (Final Answer)**：对于中文语境的问题，最终答案应使用中文回应

    """

        return prompt

    def generate_summarize_prompt(
        self,
        task_description: str,
        task_failed: bool = False,
        chinese_context: bool = False,
    ) -> str:
        summarize_prompt = (
            (
                "This is a direct instruction to you (the assistant), not the result of a tool call.\n\n"
            )
            + (
                "**Important: You have either exhausted the context token limit or reached the maximum number of interaction turns without arriving at a conclusive answer. Therefore, you failed to complete the task. You Must explicitly state that you failed to complete the task in your response.**\n\n"
                if task_failed
                else ""
            )
            + (
                "We are now ending this session, and your conversation history will be deleted. "
                "You must NOT initiate any further tool use. This is your final opportunity to report "
                "*all* of the information gathered during the session.\n\n"
                "Summarize the above conversation, and output the FINAL ANSWER to the original question.\n\n"
                "If a clear answer has already been provided earlier in the conversation, do not rethink or recalculate it — "
                "simply extract that answer and reformat it to match the required format below.\n"
                "If a definitive answer could not be determined, make a well-informed educated guess based on the conversation.\n\n"
                "The original question is repeated here for reference:\n\n"
                f"---\n{task_description}\n---\n\n"
                "Summarize ALL working history for this task, including your step-by-step thoughts, all tool calls, and all tool results (i.e., the full solving trajectory so far).\n"
                "Output the FINAL ANSWER and detailed supporting information of the task given to you.\n\n"
                "If you found any useful facts, data, or quotes directly relevant to the original task, include them clearly and completely.\n"
                "If you reached a conclusion or answer, include it as part of the response.\n"
                "If the task could not be fully answered, return all partially relevant findings, search results, quotes, and observations that might help a downstream agent solve the problem.\n"
                "If partial, conflicting, or inconclusive information was found, clearly indicate this in your response.\n\n"
                "Your final response should be a clear, complete, and structured report.\n"
                "Organize the content into logical sections with appropriate headings.\n"
                "Do NOT include any tool call instructions, speculative filler, or vague summaries.\n"
                "Focus on factual, specific, and well-organized information.\n\n"
                "**Important: Always respond in the same language as the original question. For example, if the original question is in Chinese, respond in Chinese; if it is in English, respond in English. This applies to any language — match the language of your response to the language of the question.**"
            )
        )

        # Add Chinese-specific summary instructions
        if chinese_context:
            summarize_prompt += """

## 中文总结要求

如果原始问题涉及中文语境：
- **总结语言**：使用中文进行总结和回答
- **思考过程**：回顾和总结思考过程时也应使用中文表达
- **信息组织**：保持中文信息的原始格式和表达方式
- **过程描述**：对工作历史、步骤描述、结果分析等各种输出都应使用中文
- **最终答案**：确保最终答案符合中文表达习惯和用户期望
"""
        return summarize_prompt
