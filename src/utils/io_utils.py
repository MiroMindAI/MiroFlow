# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import os

from src.logging.logger import bootstrap_logger


LOGGER_LEVEL = os.getenv("LOGGER_LEVEL", "INFO")
logger = bootstrap_logger(level=LOGGER_LEVEL)


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
        # Get the absolute path of the file
        absolute_file_path = os.path.abspath(task_file_name)
        updated_task_description += f"\nNote: A {file_type} file '{task_file_name}' is associated with this task. If you need worker agent to read its content, you should provide the complete local system file path: {absolute_file_path}.\n\n"

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
        Uses balanced brace counting to handle arbitrary levels of nested braces correctly.
        Returns the last matched content, or empty string if no match found.
        """
        if not text:
            return ""

        matches = []
        i = 0

        while i < len(text):
            # Find the next \boxed{ pattern
            boxed_start = text.find(r"\boxed{", i)
            if boxed_start == -1:
                break

            # Start after the opening brace
            content_start = boxed_start + 7  # len(r'\boxed{') = 7
            if content_start >= len(text):
                break

            # Count balanced braces
            brace_count = 1
            content_end = content_start

            while content_end < len(text) and brace_count > 0:
                char = text[content_end]
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                content_end += 1

            # If we found a balanced match (brace_count == 0)
            if brace_count == 0:
                content = text[
                    content_start : content_end - 1
                ]  # -1 to exclude the closing brace
                matches.append(content)
                # Continue searching from after this complete match
                i = content_end
            else:
                # If braces are unbalanced, skip this \boxed{ and continue searching
                i = content_start

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

        return "\n".join(summary_lines), boxed_result
