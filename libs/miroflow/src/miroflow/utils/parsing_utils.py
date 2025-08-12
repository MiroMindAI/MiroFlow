# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import json
import re

import json5

from miroflow.logging.logger import bootstrap_logger

logger = bootstrap_logger()


def robust_json_loads(json_str):
    """
    Robust JSON parsing function, first try standard json, fallback to json5 if that fails

    Args:
        json_str (str): The JSON string to parse

    Returns:
        dict: The parsed JSON object

    Raises:
        json.JSONDecodeError: If all parsing attempts fail
    """
    # First try standard json
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug(f"Standard JSON parsing failed: {e}")

        # If json5 is available, try json5 parsing
        if json5 is not None:
            try:
                return json5.loads(json_str)
            except Exception as e2:
                logger.debug(f"JSON5 parsing also failed: {e2}")

        # If both fail, re-raise the original exception
        raise e


def escape_string_content(content, key_name=None):
    """
    Smart escaping and fixing: different processing based on key type

    Escaping strategy:
    - Basic escaping: double quotes, newlines and other JSON-required escaping
    - Smart fixing: fix common syntax errors based on key type
      * code_block: null→None, true→True, false→False
      * command: True→true, False→false, None→""
      * others: None→null, True→true, False→false

    Args:
        content (str): The string content to escape
        key_name (str): The key name, used to determine fixing strategy

    Returns:
        str: The escaped and fixed string
    """
    # Strategy 1: Basic escaping (needed for all fields)
    result = []
    i = 0

    while i < len(content):
        char = content[i]

        if char == "\\" and i + 1 < len(content):
            # Found backslash, keep escape sequence as is (including \" and \\n etc.)
            result.append(char)  # Add backslash
            result.append(content[i + 1])  # Add next character
            i += 2  # Skip two characters

        elif char == '"':
            # Unescaped double quote, needs escaping
            result.append('\\"')
            i += 1

        elif char == "\n":
            # Unescaped newline, needs escaping (JSON standard requirement)
            result.append("\\n")
            i += 1

        elif char == "\r":
            # Unescaped carriage return, needs escaping
            result.append("\\r")
            i += 1

        else:
            # Other characters remain as is
            result.append(char)
            i += 1

    content_escaped = "".join(result)

    # Strategy 2: Smart fixing based on key type
    if key_name == "code_block":
        # Python code fixing
        content_escaped = fix_python_syntax(content_escaped)
    elif key_name == "command":
        # Shell command fixing
        content_escaped = fix_shell_syntax(content_escaped)
    else:
        # General JSON fixing
        content_escaped = fix_json_syntax(content_escaped)

    return content_escaped


def fix_python_syntax(content):
    """Fix common syntax errors in Python code"""
    import re

    # Keywords that need to be kept in Python
    # null → None (but be careful not to change null inside strings)
    content = re.sub(r"\bnull\b", "None", content)
    # true → True
    content = re.sub(r"\btrue\b", "True", content)
    # false → False
    content = re.sub(r"\bfalse\b", "False", content)

    # Fix common Python syntax errors
    # e.g.: print "text" → print("text") (Python 2 to 3)
    content = re.sub(r'\bprint\s+"([^"]*)"', r'print("\1")', content)

    return content


def fix_shell_syntax(content):
    """Fix common syntax errors in Shell commands"""
    import re

    # Keyword fixes in Shell
    # true/false are usually lowercase in shell
    content = re.sub(r"\bTrue\b", "true", content)
    content = re.sub(r"\bFalse\b", "false", content)
    content = re.sub(
        r"\bNone\b", '""', content
    )  # None is usually empty string in shell

    # Fix common shell syntax issues
    # e.g.: ensure variable references are correct

    return content


def fix_json_syntax(content):
    """Fix common errors in JSON strings"""
    import re

    # JSON standard keyword fixes
    # Python keywords → JSON keywords
    content = re.sub(r"\bNone\b", "null", content)
    content = re.sub(r"\bTrue\b", "true", content)
    content = re.sub(r"\bFalse\b", "false", content)

    return content


def parse_escaped_json_string(raw_str):
    """
    Fix escape issues in JSON strings, supports smart syntax fixing

    Uses 5 progressive parsing strategies:
    1. Direct parsing - return directly if already valid JSON
    2. Line start pattern - use simple line start key pattern for parsing
    3. Negative lookbehind pattern - use complex negative lookbehind to exclude escaped keys
    4. Legacy method - use historically compatible simple string replacement
    5. Conservative fallback - most basic escape fixing

    Args:
        raw_str (str): JSON string that may contain escape issues

    Returns:
        str: Fixed valid JSON string

    Raises:
        json.JSONDecodeError: If all strategies fail to fix into valid JSON
    """
    raw_str = raw_str.strip()

    # Strategy 1: Direct parsing verification
    if _try_direct_parse(raw_str):
        return raw_str

    # Strategy 2: Line start pattern parsing
    result = _try_line_start_pattern(raw_str)
    if result:
        return result

    # Strategy 3: Negative lookbehind pattern parsing
    result = _try_negative_lookbehind_pattern(raw_str)
    if result:
        return result

    # Strategy 4: Legacy method
    result = _try_legacy_method(raw_str)
    if result:
        return result

    # Strategy 5: Conservative fallback
    return _conservative_escape_fallback(raw_str)


def _try_direct_parse(raw_str):
    """Strategy 1: Try direct parsing, no fixing needed if successful"""
    try:
        robust_json_loads(raw_str)
        return True
    except json.JSONDecodeError:
        return False


def _try_line_start_pattern(raw_str):
    """Strategy 2: Use line start pattern for parsing"""
    return _try_parse_with_pattern(raw_str, r'^\s*"([\w\-_]+)"\s*:')


def _try_negative_lookbehind_pattern(raw_str):
    """Strategy 3: Use negative lookbehind pattern for parsing"""
    return _try_parse_with_pattern(raw_str, r'(?<!\\)"([\w\-_]+)"\s*:')


def _try_legacy_method(raw_str):
    """Strategy 4: Try legacy simple method"""
    try:
        corrected_json = _legacy_escape_method(raw_str)
        robust_json_loads(corrected_json)
        return corrected_json
    except (json.JSONDecodeError, Exception):
        return None


def _try_parse_with_pattern(raw_str, pattern):
    """General key pattern-based parsing method"""
    import re

    try:
        # Add multiline flag if it's a line start pattern
        flags = re.MULTILINE if pattern.startswith(r"^\s*") else 0
        key_matches = list(re.finditer(pattern, raw_str, flags))
        if not key_matches:
            return None

        result = []
        last_end = 0

        for i, key_match in enumerate(key_matches):
            key_name = key_match.group(1)
            key_end = key_match.end()

            # Add content before key (including key itself)
            result.append(raw_str[last_end:key_end])

            # Skip whitespace, find the start quote of value
            value_start_pos = key_end
            while value_start_pos < len(raw_str) and raw_str[value_start_pos] in " \t":
                value_start_pos += 1

            if value_start_pos >= len(raw_str) or raw_str[value_start_pos] != '"':
                # Not a string value, skip
                last_end = key_end
                continue

            # Skip the start quote
            value_content_start = value_start_pos + 1

            # Find the end position of value
            if i < len(key_matches) - 1:
                search_limit = key_matches[i + 1].start()
            else:
                search_limit = len(raw_str)

            # Search backwards for value end marker
            value_end_pos = _find_value_end_position(
                raw_str, value_content_start, search_limit
            )
            if value_end_pos is None:
                last_end = key_end
                continue

            # Extract and escape value content
            value_content = raw_str[value_content_start:value_end_pos]
            escaped_value = escape_string_content(value_content, key_name)

            # Add fixed value
            result.append(' "')
            result.append(escaped_value)
            result.append('"')

            last_end = value_end_pos + 1

        # Add remaining content
        result.append(raw_str[last_end:])
        corrected_json = "".join(result)

        # Verify fix result
        robust_json_loads(corrected_json)
        return corrected_json

    except (json.JSONDecodeError, re.error, Exception):
        return None


def _find_value_end_position(raw_str, start_pos, search_limit):
    """Find the end position of value"""
    for pos in range(search_limit - 1, start_pos, -1):
        if raw_str[pos] == '"':
            after_quote = raw_str[pos + 1 : search_limit].strip()
            if (
                after_quote.startswith(",")
                or after_quote.startswith("}")
                or after_quote == ""
            ):
                return pos
    return None


def _legacy_escape_method(raw_str):
    """
    Legacy simple escape method: mainly handles special cases of code_block field
    """
    # Remove leading and trailing whitespace
    raw_str = raw_str.strip()

    # Check if contains code_block field, which needs special handling
    if '"code_block": "' in raw_str:
        # Split into two parts: first part and code content part
        parts = raw_str.split('"code_block": "', 1)
        if len(parts) != 2:
            raise ValueError("Unable to correctly split code_block field")

        # First part: handle escape sequences normally
        first_part = parts[0].replace("\\n", "\n")

        # Second part: code content needs special handling
        second_part = parts[1]

        # Find the end position of code content (should end with "\n})
        if second_part.endswith("\n}"):
            code_content = second_part[:-2]  # Remove the last \n}
        elif second_part.endswith('"\\n}'):
            code_content = second_part[:-4]  # Remove the last "\n}
        else:
            # Find the last " character as code content end
            last_quote = second_part.rfind('"')
            if last_quote == -1:
                raise ValueError("Unable to find end position of code content")
            code_content = second_part[:last_quote]

        # Escape special characters in code content
        # Note the order: escape backslashes first, then quotes, finally handle newlines
        code_content_escaped = (
            code_content.replace("\\", "\\\\")  # Escape backslashes
            .replace('"', '\\"')  # Escape quotes
            .replace("\n", "\\n")
        )  # Keep newlines as escaped format

        # Reassemble the complete JSON string
        corrected_json = first_part + '"code_block": "' + code_content_escaped + '"\n}'

    else:
        # Simple case without code_block, directly replace escape sequences
        corrected_json = raw_str.replace("\\n", "\n").replace("\\\\", "\\")

    return corrected_json


def _conservative_escape_fallback(raw_str):
    """
    Conservative fallback strategy: only fix the most obvious issues
    """
    import re

    # Only handle the most common issue: newlines in string values
    def fix_newlines(match):
        key = match.group(1)
        value = match.group(2)

        # Only escape newlines, keep it simple
        fixed_value = value.replace("\n", "\\n").replace("\r", "\\r")
        return f'"{key}": "{fixed_value}"'

    # Use most conservative regex pattern
    pattern = r'"([^"]+)":\s*"([^"]*)"'

    try:
        return re.sub(pattern, fix_newlines, raw_str)
    except re.error:
        # If even this fails, return original string directly
        return raw_str


def parse_llm_response_for_tool_calls(llm_response_content_text):
    """
    Parse tool_calls or <use_mcp_tool> tags from LLM response text.
    Returns a list containing tool call information.
    """
    # tool_calls or MCP reponse are handled differently
    # for openai response api, the tool_calls are in the response text
    if isinstance(llm_response_content_text, dict):
        tool_calls = []
        bad_tool_calls = []
        for item in llm_response_content_text.get("output", []):
            if item.get("type") == "function_call":
                server_name, tool_name = item.get("name").rsplit("-", maxsplit=1)
                arguments_str = item.get("arguments")
                try:
                    # Try to handle possible newlines and escape characters
                    arguments = robust_json_loads(arguments_str)
                except json.JSONDecodeError:
                    logger.debug(
                        f"Warning: Unable to parse tool arguments JSON: {arguments_str}"
                    )
                    # Try more lenient parsing or log error
                    try:
                        # Try to replace some common error formats, e.g. Python dict strings
                        arguments_str_fixed = (
                            arguments_str.replace("'", '"')
                            .replace("None", "null")
                            .replace("True", "true")
                            .replace("False", "false")
                        )
                        arguments = robust_json_loads(arguments_str_fixed)
                        logger.debug(
                            "Info: Attempted fix and successfully parsed arguments."
                        )
                    except json.JSONDecodeError:
                        logger.debug(
                            f"Error: Still unable to parse tool arguments JSON after fix: {arguments_str}"
                        )
                        arguments = {
                            "error": "Failed to parse arguments",
                            "raw": arguments_str,
                        }
                tool_calls.append(
                    dict(
                        server_name=server_name,
                        tool_name=tool_name,
                        arguments=arguments,
                        id=item.get("call_id"),
                    )
                )
        return tool_calls, bad_tool_calls

    # for openai completion api, the tool_calls are in the response text
    if isinstance(llm_response_content_text, list):
        tool_calls = []
        bad_tool_calls = []
        for tool_call in llm_response_content_text:
            server_name, tool_name = tool_call.function.name.rsplit("-", maxsplit=1)
            arguments_str = tool_call.function.arguments

            # Parse JSON string to dictionary
            try:
                # Try to handle possible newlines and escape characters
                arguments = robust_json_loads(arguments_str)
            except json.JSONDecodeError:
                logger.debug(
                    f"Warning: Unable to parse tool arguments JSON: {arguments_str}"
                )
                # Try more lenient parsing or log error
                try:
                    # Try to replace some common error formats, e.g. Python dict strings
                    arguments_str_fixed = (
                        arguments_str.replace("'", '"')
                        .replace("None", "null")
                        .replace("True", "true")
                        .replace("False", "false")
                    )
                    arguments = robust_json_loads(arguments_str_fixed)
                    logger.debug(
                        "Info: Attempted fix and successfully parsed arguments."
                    )
                except json.JSONDecodeError:
                    logger.debug(
                        f"Error: Still unable to parse tool arguments JSON after fix: {arguments_str}"
                    )
                    arguments = {
                        "error": "Failed to parse arguments",
                        "raw": arguments_str,
                    }

            tool_calls.append(
                dict(
                    server_name=server_name,
                    tool_name=tool_name,
                    arguments=arguments,
                    id=tool_call.id,
                )
            )
        return tool_calls, bad_tool_calls

    # for other clients, such as qwen and anthropic, we use MCP instead of tool calls
    tool_calls = []
    bad_tool_calls = []
    # Find all <use_mcp_tool> tags, using more robust regular expressions
    # Allow more whitespace, case insensitive, allow tag attributes
    tool_call_patterns = re.findall(
        r"<use_mcp_tool[^>]*?>\s*<server_name[^>]*?>(.*?)</server_name>\s*<tool_name[^>]*?>(.*?)</tool_name>\s*<arguments[^>]*?>\s*([\s\S]*?)\s*</arguments>\s*</use_mcp_tool>",
        llm_response_content_text,
        re.DOTALL | re.IGNORECASE,
    )

    # Check for invalid tool calls
    # Find all possible incomplete or malformed <use_mcp_tool> tags, using more robust regular expressions
    incomplete_patterns = [
        r"<use_mcp_tool[^>]*?>(?:(?!</use_mcp_tool>).)*?(?:</use_mcp_tool>|$)",  # Complete or incomplete tool calls
        r"<server_name[^>]*?>(?:(?!</server_name>).)*?(?:</server_name>|$)",  # Server name tags
        r"<tool_name[^>]*?>(?:(?!</tool_name>).)*?(?:</tool_name>|$)",  # Tool name tags
        r"<arguments[^>]*?>(?:(?!</arguments>).)*?(?:</arguments>|$)",  # Arguments tags
    ]

    # Check each pattern for incomplete tags
    for pattern in incomplete_patterns:
        matches = re.findall(
            pattern, llm_response_content_text, re.DOTALL | re.IGNORECASE
        )
        for match in matches:
            # Check if closing tags are missing (case insensitive)
            if pattern.endswith("</server_name>|$)") and not re.search(
                r"</server_name>\s*$", match, re.IGNORECASE
            ):
                bad_tool_calls.append(
                    {"error": "Unclosed server_name tag", "content": match}
                )
            elif pattern.endswith("</tool_name>|$)") and not re.search(
                r"</tool_name>\s*$", match, re.IGNORECASE
            ):
                bad_tool_calls.append(
                    {"error": "Unclosed tool_name tag", "content": match}
                )
            elif pattern.endswith("</arguments>|$)") and not re.search(
                r"</arguments>\s*$", match, re.IGNORECASE
            ):
                bad_tool_calls.append(
                    {"error": "Unclosed arguments tag", "content": match}
                )
            elif pattern.endswith("</use_mcp_tool>|$)") and not re.search(
                r"</use_mcp_tool>\s*$", match, re.IGNORECASE
            ):
                bad_tool_calls.append(
                    {"error": "Unclosed use_mcp_tool tag", "content": match}
                )

    # If invalid tool calls are found, log warnings
    if bad_tool_calls:
        logger.debug(f"Warning: Found {len(bad_tool_calls)} invalid tool calls")
        for bad_call in bad_tool_calls:
            logger.debug(
                f"Invalid tool call: {bad_call['error']} - {bad_call['content'][:100]}..."
            )

    for match in tool_call_patterns:
        server_name = match[0].strip()
        tool_name = match[1].strip()
        arguments_str = match[2].strip()

        # Parse JSON string to dictionary
        try:
            # Try to handle possible newlines and escape characters
            arguments = robust_json_loads(arguments_str)
        except json.JSONDecodeError:
            logger.debug(
                f"Warning: Unable to parse tool arguments JSON: {arguments_str}"
            )
            # Try more lenient parsing or log error
            try:
                # Uniformly use smart JSON fixing, no longer special handling for specific tools
                arguments_str_fixed = parse_escaped_json_string(arguments_str)
                arguments = robust_json_loads(arguments_str_fixed)
                logger.debug("Info: Attempted fix and successfully parsed arguments.")
            except json.JSONDecodeError:
                logger.debug(
                    f"Error: Still unable to parse tool arguments JSON after fix: {arguments_str}"
                )
                arguments = {"error": "Failed to parse arguments", "raw": arguments_str}

        tool_calls.append(
            {
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
                "id": None,
            }
        )

    for item in bad_tool_calls:
        if item["error"] == "Unclosed arguments tag":
            # Try to fix missing </arguments> case
            content = llm_response_content_text
            if content.find("<arguments>") != -1 and content.find("</arguments>") == -1:
                # Find <arguments> start position
                args_start = content.find("<arguments>") + len("<arguments>")
                # Find next </ tag as end position
                next_tag = content.find("</", args_start)
                if next_tag != -1:
                    # Add </arguments> before next tag
                    fixed_content = (
                        content[:next_tag] + "</arguments>" + content[next_tag:]
                    )
                else:
                    # If no next tag, add </arguments> at the end
                    fixed_content = content + "</arguments>"

                logger.info(
                    "Attempting to fix tool call with missing </arguments>, re-parsing..."
                )
                # Recursively call self to re-parse fixed content
                return parse_llm_response_for_tool_calls(fixed_content)

    return tool_calls, bad_tool_calls


def main():
    """Simple debug entry point for testing parsing functionality"""
    # Simple test case
    test_case = 'Let\'s check if there are any numbered references in the paper:\n\n<use_mcp_tool>\n<server_name>tool-code</server_name>\n<tool_name>run_command</tool_name>\n<arguments>\n{\n"sandbox_id": "i86ayus8ryxxtaifen3bg",\n"command": "pdfgrep -i \'\\\\[[0-9]\\\\]\' /home/user/48_2009-CJFS.pdf"\n}\n</arguments>\n</use_mcp_tool>'

    # Parse test
    tool_calls, bad_tool_calls = parse_llm_response_for_tool_calls(test_case)

    print(f"Parse result: {len(tool_calls)} tool calls, {len(bad_tool_calls)} errors")
    if tool_calls:
        args = tool_calls[0]["arguments"]
        print(f"Arguments: {list(args.keys())}")
        for key, value in args.items():
            print(f"{key}:\n{value}\n")

    print("Debug completed")
