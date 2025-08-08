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
    鲁棒的JSON解析函数，首先尝试标准json，失败时尝试json5

    Args:
        json_str (str): 要解析的JSON字符串

    Returns:
        dict: 解析后的JSON对象

    Raises:
        json.JSONDecodeError: 如果所有解析尝试都失败
    """
    # 首先尝试标准json
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.debug(f"标准JSON解析失败: {e}")

        # 如果有json5，尝试使用json5解析
        if json5 is not None:
            try:
                return json5.loads(json_str)
            except Exception as e2:
                logger.debug(f"JSON5解析也失败: {e2}")

        # 如果都失败了，重新抛出原始异常
        raise e


def escape_string_content(content, key_name=None):
    """
    智能转义和修复：根据key类型进行不同的处理

    转义策略：
    - 基础转义：双引号、换行符等JSON必需的转义
    - 智能修复：根据key类型修复常见语法错误
      * code_block: null→None, true→True, false→False
      * command: True→true, False→false, None→""
      * 其他: None→null, True→true, False→false

    Args:
        content (str): 要转义的字符串内容
        key_name (str): key的名称，用于确定修复策略

    Returns:
        str: 转义并修复后的字符串
    """
    # 策略1：基础转义（所有字段都需要）
    result = []
    i = 0

    while i < len(content):
        char = content[i]

        if char == "\\" and i + 1 < len(content):
            # 发现反斜杠，保持转义序列原样（包括 \" 和 \\n 等）
            result.append(char)  # 添加反斜杠
            result.append(content[i + 1])  # 添加下一个字符
            i += 2  # 跳过两个字符

        elif char == '"':
            # 未转义的双引号，需要转义
            result.append('\\"')
            i += 1

        elif char == "\n":
            # 未转义的换行符，需要转义（JSON标准要求）
            result.append("\\n")
            i += 1

        elif char == "\r":
            # 未转义的回车符，需要转义
            result.append("\\r")
            i += 1

        else:
            # 其他字符直接保持原样
            result.append(char)
            i += 1

    content_escaped = "".join(result)

    # 策略2：根据key类型进行智能修复
    if key_name == "code_block":
        # Python代码修复
        content_escaped = fix_python_syntax(content_escaped)
    elif key_name == "command":
        # Shell命令修复
        content_escaped = fix_shell_syntax(content_escaped)
    else:
        # 通用JSON修复
        content_escaped = fix_json_syntax(content_escaped)

    return content_escaped


def fix_python_syntax(content):
    """修复Python代码中的常见语法错误"""
    import re

    # Python中需要保持的关键词
    # null → None（但要小心不要误改字符串中的null）
    content = re.sub(r"\bnull\b", "None", content)
    # true → True
    content = re.sub(r"\btrue\b", "True", content)
    # false → False
    content = re.sub(r"\bfalse\b", "False", content)

    # 修复常见的Python语法错误
    # 例如：print "text" → print("text")（Python 2 to 3）
    content = re.sub(r'\bprint\s+"([^"]*)"', r'print("\1")', content)

    return content


def fix_shell_syntax(content):
    """修复Shell命令中的常见语法错误"""
    import re

    # Shell中的关键词修复
    # true/false在shell中通常是小写
    content = re.sub(r"\bTrue\b", "true", content)
    content = re.sub(r"\bFalse\b", "false", content)
    content = re.sub(r"\bNone\b", '""', content)  # None在shell中通常用空字符串

    # 修复常见的shell语法问题
    # 例如：确保变量引用正确

    return content


def fix_json_syntax(content):
    """修复JSON字符串中的常见错误"""
    import re

    # JSON标准关键词修复
    # Python关键词 → JSON关键词
    content = re.sub(r"\bNone\b", "null", content)
    content = re.sub(r"\bTrue\b", "true", content)
    content = re.sub(r"\bFalse\b", "false", content)

    return content


def parse_escaped_json_string(raw_str):
    """
    修复JSON字符串中的转义问题，支持智能语法修复

    采用5种策略的渐进式解析：
    1. 直接解析 - 如果已经是有效JSON就直接返回
    2. 行开始模式 - 使用简单的行开始key模式进行解析
    3. 负向后瞻模式 - 使用复杂的负向后瞻排除转义key
    4. 老版本方法 - 使用历史兼容的简单字符串替换
    5. 保守回退 - 最基本的转义修复

    Args:
        raw_str (str): 可能包含转义问题的JSON字符串

    Returns:
        str: 修复后的有效JSON字符串

    Raises:
        json.JSONDecodeError: 如果所有策略都无法修复为有效JSON
    """
    raw_str = raw_str.strip()

    # 策略1：直接解析验证
    if _try_direct_parse(raw_str):
        return raw_str

    # 策略2：行开始模式解析
    result = _try_line_start_pattern(raw_str)
    if result:
        return result

    # 策略3：负向后瞻模式解析
    result = _try_negative_lookbehind_pattern(raw_str)
    if result:
        return result

    # 策略4：老版本方法
    result = _try_legacy_method(raw_str)
    if result:
        return result

    # 策略5：保守回退
    return _conservative_escape_fallback(raw_str)


def _try_direct_parse(raw_str):
    """策略1：尝试直接解析，如果成功就不需要修复"""
    try:
        robust_json_loads(raw_str)
        return True
    except json.JSONDecodeError:
        return False


def _try_line_start_pattern(raw_str):
    """策略2：使用行开始模式进行解析"""
    return _try_parse_with_pattern(raw_str, r'^\s*"([\w\-_]+)"\s*:')


def _try_negative_lookbehind_pattern(raw_str):
    """策略3：使用负向后瞻模式进行解析"""
    return _try_parse_with_pattern(raw_str, r'(?<!\\)"([\w\-_]+)"\s*:')


def _try_legacy_method(raw_str):
    """策略4：尝试老版本的简单方法"""
    try:
        corrected_json = _legacy_escape_method(raw_str)
        robust_json_loads(corrected_json)
        return corrected_json
    except (json.JSONDecodeError, Exception):
        return None


def _try_parse_with_pattern(raw_str, pattern):
    """通用的基于key模式的解析方法"""
    import re

    try:
        # 如果是行开始模式，需要添加多行标志
        flags = re.MULTILINE if pattern.startswith(r"^\s*") else 0
        key_matches = list(re.finditer(pattern, raw_str, flags))
        if not key_matches:
            return None

        result = []
        last_end = 0

        for i, key_match in enumerate(key_matches):
            key_name = key_match.group(1)
            key_end = key_match.end()

            # 添加key之前的内容（包括key本身）
            result.append(raw_str[last_end:key_end])

            # 跳过空白字符，找到value的开始引号
            value_start_pos = key_end
            while value_start_pos < len(raw_str) and raw_str[value_start_pos] in " \t":
                value_start_pos += 1

            if value_start_pos >= len(raw_str) or raw_str[value_start_pos] != '"':
                # 不是字符串值，跳过
                last_end = key_end
                continue

            # 跳过开始引号
            value_content_start = value_start_pos + 1

            # 找到value的结束位置
            if i < len(key_matches) - 1:
                search_limit = key_matches[i + 1].start()
            else:
                search_limit = len(raw_str)

            # 反向查找value结束标记
            value_end_pos = _find_value_end_position(
                raw_str, value_content_start, search_limit
            )
            if value_end_pos is None:
                last_end = key_end
                continue

            # 提取并转义value内容
            value_content = raw_str[value_content_start:value_end_pos]
            escaped_value = escape_string_content(value_content, key_name)

            # 添加修复后的value
            result.append(' "')
            result.append(escaped_value)
            result.append('"')

            last_end = value_end_pos + 1

        # 添加剩余内容
        result.append(raw_str[last_end:])
        corrected_json = "".join(result)

        # 验证修复结果
        robust_json_loads(corrected_json)
        return corrected_json

    except (json.JSONDecodeError, re.error, Exception):
        return None


def _find_value_end_position(raw_str, start_pos, search_limit):
    """查找value的结束位置"""
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
    老版本的简单转义方法：主要处理code_block字段的特殊情况
    """
    # 去除首尾空白
    raw_str = raw_str.strip()

    # 检查是否包含 code_block 字段，这需要特殊处理
    if '"code_block": "' in raw_str:
        # 分割为两部分：前半部分和代码内容部分
        parts = raw_str.split('"code_block": "', 1)
        if len(parts) != 2:
            raise ValueError("无法正确分割 code_block 字段")

        # 前半部分：正常处理转义序列
        first_part = parts[0].replace("\\n", "\n")

        # 后半部分：代码内容需要特殊处理
        second_part = parts[1]

        # 找到代码内容的结束位置（应该以 "\n} 结尾）
        if second_part.endswith("\n}"):
            code_content = second_part[:-2]  # 移除最后的 \n}
        elif second_part.endswith('"\\n}'):
            code_content = second_part[:-4]  # 移除最后的 "\n}
        else:
            # 寻找最后一个 " 字符作为代码内容结束
            last_quote = second_part.rfind('"')
            if last_quote == -1:
                raise ValueError("无法找到代码内容的结束位置")
            code_content = second_part[:last_quote]

        # 转义代码内容中的特殊字符
        # 注意顺序：先转义反斜杠，再转义引号，最后处理换行符
        code_content_escaped = (
            code_content.replace("\\", "\\\\")  # 转义反斜杠
            .replace('"', '\\"')  # 转义引号
            .replace("\n", "\\n")
        )  # 换行符保持为转义格式

        # 重新组装完整的JSON字符串
        corrected_json = first_part + '"code_block": "' + code_content_escaped + '"\n}'

    else:
        # 不包含 code_block 的简单情况，直接替换转义序列
        corrected_json = raw_str.replace("\\n", "\n").replace("\\\\", "\\")

    return corrected_json


def _conservative_escape_fallback(raw_str):
    """
    保守的fallback策略：只修复最明显的问题
    """
    import re

    # 只处理最常见的问题：字符串值中的换行符
    def fix_newlines(match):
        key = match.group(1)
        value = match.group(2)

        # 只转义换行符，保持简单
        fixed_value = value.replace("\n", "\\n").replace("\r", "\\r")
        return f'"{key}": "{fixed_value}"'

    # 使用最保守的正则模式
    pattern = r'"([^"]+)":\s*"([^"]*)"'

    try:
        return re.sub(pattern, fix_newlines, raw_str)
    except re.error:
        # 如果连这个都失败了，直接返回原字符串
        return raw_str


def parse_llm_response_for_tool_calls(llm_response_content_text):
    """
    从 LLM 响应文本中解析 tool_calls 或 <use_mcp_tool> 标记。
    返回一个包含工具调用信息的列表。
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
                    # 尝试处理可能存在的换行符和转义符
                    arguments = robust_json_loads(arguments_str)
                except json.JSONDecodeError:
                    logger.debug(f"警告: 无法解析工具参数 JSON: {arguments_str}")
                    # 尝试更宽松的解析或记录错误
                    try:
                        # 尝试替换掉一些常见的错误格式，例如 Python 的 dict 字符串
                        arguments_str_fixed = (
                            arguments_str.replace("'", '"')
                            .replace("None", "null")
                            .replace("True", "true")
                            .replace("False", "false")
                        )
                        arguments = robust_json_loads(arguments_str_fixed)
                        logger.debug("信息: 已尝试修复并成功解析参数。")
                    except json.JSONDecodeError:
                        logger.debug(
                            f"错误: 修复后仍无法解析工具参数 JSON: {arguments_str}"
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

            # 解析 JSON 字符串为字典
            try:
                # 尝试处理可能存在的换行符和转义符
                arguments = robust_json_loads(arguments_str)
            except json.JSONDecodeError:
                logger.debug(f"警告: 无法解析工具参数 JSON: {arguments_str}")
                # 尝试更宽松的解析或记录错误
                try:
                    # 尝试替换掉一些常见的错误格式，例如 Python 的 dict 字符串
                    arguments_str_fixed = (
                        arguments_str.replace("'", '"')
                        .replace("None", "null")
                        .replace("True", "true")
                        .replace("False", "false")
                    )
                    arguments = robust_json_loads(arguments_str_fixed)
                    logger.debug("信息: 已尝试修复并成功解析参数。")
                except json.JSONDecodeError:
                    logger.debug(
                        f"错误: 修复后仍无法解析工具参数 JSON: {arguments_str}"
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
    # 查找所有 <use_mcp_tool> 标记，使用更鲁棒的正则表达式
    # 允许更多的空白字符，大小写不敏感，允许标签属性
    tool_call_patterns = re.findall(
        r"<use_mcp_tool[^>]*?>\s*<server_name[^>]*?>(.*?)</server_name>\s*<tool_name[^>]*?>(.*?)</tool_name>\s*<arguments[^>]*?>\s*([\s\S]*?)\s*</arguments>\s*</use_mcp_tool>",
        llm_response_content_text,
        re.DOTALL | re.IGNORECASE,
    )

    # 检查是否有不合法的工具调用
    # 查找所有可能的不完整或格式错误的 <use_mcp_tool> 标记，使用更鲁棒的正则表达式
    incomplete_patterns = [
        r"<use_mcp_tool[^>]*?>(?:(?!</use_mcp_tool>).)*?(?:</use_mcp_tool>|$)",  # 完整或不完整的工具调用
        r"<server_name[^>]*?>(?:(?!</server_name>).)*?(?:</server_name>|$)",  # 服务器名称标签
        r"<tool_name[^>]*?>(?:(?!</tool_name>).)*?(?:</tool_name>|$)",  # 工具名称标签
        r"<arguments[^>]*?>(?:(?!</arguments>).)*?(?:</arguments>|$)",  # 参数标签
    ]

    # 检查每个模式是否有不完整的标签
    for pattern in incomplete_patterns:
        matches = re.findall(
            pattern, llm_response_content_text, re.DOTALL | re.IGNORECASE
        )
        for match in matches:
            # 检查是否缺少闭合标签（忽略大小写）
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

    # 如果发现不合法的工具调用，记录警告
    if bad_tool_calls:
        logger.debug(f"警告: 发现 {len(bad_tool_calls)} 个不合法的工具调用")
        for bad_call in bad_tool_calls:
            logger.debug(
                f"不合法工具调用: {bad_call['error']} - {bad_call['content'][:100]}..."
            )

    for match in tool_call_patterns:
        server_name = match[0].strip()
        tool_name = match[1].strip()
        arguments_str = match[2].strip()

        # 解析 JSON 字符串为字典
        try:
            # 尝试处理可能存在的换行符和转义符
            arguments = robust_json_loads(arguments_str)
        except json.JSONDecodeError:
            logger.debug(f"警告: 无法解析工具参数 JSON: {arguments_str}")
            # 尝试更宽松的解析或记录错误
            try:
                # 统一使用智能JSON修复，不再特殊处理某个工具
                arguments_str_fixed = parse_escaped_json_string(arguments_str)
                arguments = robust_json_loads(arguments_str_fixed)
                logger.debug("信息: 已尝试修复并成功解析参数。")
            except json.JSONDecodeError:
                logger.debug(f"错误: 修复后仍无法解析工具参数 JSON: {arguments_str}")
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
            # 尝试修复缺少 </arguments> 的情况
            content = llm_response_content_text
            if content.find("<arguments>") != -1 and content.find("</arguments>") == -1:
                # 找到 <arguments> 开始位置
                args_start = content.find("<arguments>") + len("<arguments>")
                # 查找下一个 </ 标签作为结束位置
                next_tag = content.find("</", args_start)
                if next_tag != -1:
                    # 在下一个标签前添加 </arguments>
                    fixed_content = (
                        content[:next_tag] + "</arguments>" + content[next_tag:]
                    )
                else:
                    # 如果没有下一个标签，在末尾添加 </arguments>
                    fixed_content = content + "</arguments>"

                logger.info("尝试修复缺少 </arguments> 的工具调用，重新解析...")
                # 递归调用自己重新解析修复后的内容
                return parse_llm_response_for_tool_calls(fixed_content)

    return tool_calls, bad_tool_calls


def main():
    """简单的调试入口，用于测试解析功能"""
    # 简单的测试案例
    test_case = 'Let\'s check if there are any numbered references in the paper:\n\n<use_mcp_tool>\n<server_name>tool-code</server_name>\n<tool_name>run_command</tool_name>\n<arguments>\n{\n"sandbox_id": "i86ayus8ryxxtaifen3bg",\n"command": "pdfgrep -i \'\\\\[[0-9]\\\\]\' /home/user/48_2009-CJFS.pdf"\n}\n</arguments>\n</use_mcp_tool>'

    # 解析测试
    tool_calls, bad_tool_calls = parse_llm_response_for_tool_calls(test_case)

    print(f"解析结果: {len(tool_calls)} 个工具调用, {len(bad_tool_calls)} 个错误")
    if tool_calls:
        args = tool_calls[0]["arguments"]
        print(f"参数: {list(args.keys())}")
        for key, value in args.items():
            print(f"{key}:\n{value}\n")

    print("调试完成")
