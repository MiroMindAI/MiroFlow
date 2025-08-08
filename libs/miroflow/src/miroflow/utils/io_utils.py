# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os
import re

from miroflow.logging.logger import bootstrap_logger

logger = bootstrap_logger()


def process_input(task_description, task_file_name):
    """
    Process user input, especially files.
    Returns formatted initial user message content list and updated task description.
    """
    initial_user_content = []
    updated_task_description = task_description

    # todo: add the key of `url` here for differentiating youtube wikipedia and normal url

    if task_file_name:
        if not os.path.isfile(task_file_name):
            raise FileNotFoundError(f"Error: File not found {task_file_name}")
        file_extension = task_file_name.rsplit(".", maxsplit=1)[-1].lower()
        file_type = None
        if file_extension in ["jpg", "jpeg", "png", "gif", "webp"]:
            file_type = "Image"
        elif file_extension == "txt":
            file_type = "Text"
        elif file_extension in ["jsonld", "json"]:
            file_type = "Json"
        elif file_extension in ["xlsx", "xls"]:
            file_type = "Excel"
        elif file_extension == "pdf":
            file_type = "PDF"
        elif file_extension in ["docx", "doc"]:
            file_type = "Document"
        elif file_extension in ["html", "htm"]:
            file_type = "HTML"
        elif file_extension in ["pptx", "ppt"]:
            file_type = "PPT"
        elif file_extension in ["wav"]:
            file_type = "WAV"
        elif file_extension in ["mp3", "m4a"]:
            file_type = "MP3"
        elif file_extension in ["zip"]:
            file_type = "Zip"
        else:
            file_type = file_extension
        updated_task_description += f"\nNote: A {file_type} file '{task_file_name}' is associated with this task. You should use available tools to read its content if necessary through {task_file_name}. Additionally, if you need to analyze this file by Linux commands or python codes, you should upload it to the sandbox first. Files in the sandbox cannot be accessed by other tools.\n\n"

        logger.info(
            f"Info: Detected {file_type} file {task_file_name}, added hint to description."
        )
    # output format requiremnt
    # updated_task_description += "\nYou should follow the format instruction in the question strictly and wrap the final answer in \\boxed{}."

    # Add text content (may have been updated)
    initial_user_content.append({"type": "text", "text": updated_task_description})

    return initial_user_content, updated_task_description


class OutputFormatter:
    def _extract_boxed_content(self, text: str) -> str:
        """
        Extract content from \\boxed{} patterns in the text.
        Uses safe regex patterns to avoid catastrophic backtracking.
        Returns the last matched content, or empty string if no match found.
        """
        if not text:
            return ""

        # Primary pattern: handles single-level brace nesting
        primary_pattern = r"\\boxed\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}"
        matches = re.findall(primary_pattern, text, re.DOTALL)

        # Fallback pattern: simpler match for any content until first closing brace
        if not matches:
            fallback_pattern = r"\\boxed\{([^}]+)\}"
            matches = re.findall(fallback_pattern, text, re.DOTALL)

        return matches[-1] if matches else ""

    def format_tool_result_for_user(self, tool_call_execution_result):
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

    def format_final_summary_and_log(self, final_answer_text, client=None):
        """Format final summary information, including answer and token statistics"""
        summary_lines = []
        summary_lines.append("\n" + "=" * 30 + " Final Answer " + "=" * 30)
        summary_lines.append(final_answer_text)

        # Extract boxed result - find the last match using safer regex patterns
        boxed_result = self._extract_boxed_content(final_answer_text)

        # Add extracted result section
        summary_lines.append("\n" + "-" * 20 + " Extracted Result " + "-" * 20)

        if boxed_result:
            summary_lines.append(boxed_result)
        elif final_answer_text:
            summary_lines.append("No \\boxed{} content found.")
            boxed_result = (
                "Final response is generated by LLM, but no \\boxed{} content found."
            )
        else:
            summary_lines.append("No \\boxed{} content found.")
            boxed_result = "No final answer generated."

        # Token usage statistics and cost estimation - use client method
        if client and hasattr(client, "format_token_usage_summary"):
            token_summary_lines, log_string = client.format_token_usage_summary()
            summary_lines.extend(token_summary_lines)
        else:
            # If no client or client doesn't support it, use default format
            summary_lines.append("\n" + "-" * 20 + " Token Usage & Cost " + "-" * 20)
            summary_lines.append("Token usage information not available.")
            summary_lines.append("-" * (40 + len(" Token Usage & Cost ")))
            log_string = "Token usage information not available."

        return "\n".join(summary_lines), boxed_result, log_string
