# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import json
from typing import Dict, List, Any, Optional
import re


class TraceAnalyzer:
    """
    用于分析trace JSON文件的类，方便读取和访问重要信息

    支持两种工具调用格式：
    1. 旧格式（MCP）：在content中使用XML标签格式的工具调用
    2. 新格式：在message中直接使用tool_calls字段的工具调用
    """

    def __init__(self, json_file_path: str):
        """
        初始化分析器

        Args:
            json_file_path: JSON文件的路径
        """
        self.json_file_path = json_file_path
        self.data = self._load_json()

    def _load_json(self) -> Dict[str, Any]:
        """加载JSON文件"""
        try:
            with open(self.json_file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            raise Exception(f"加载JSON文件失败: {e}")

    def _parse_new_format_tool_name(self, tool_name: str) -> tuple[str, str]:
        """
        解析新格式的工具名称

        Args:
            tool_name: 新格式的工具名称，例如：
                      - "tool-server_name-tool_name" 格式
                      - "agent-browsing-search_and_browse" 格式（浏览器代理）

        Returns:
            tuple: (server_name, actual_tool_name)
        """
        # 处理 agent-browsing-* 格式（浏览器代理调用）
        if tool_name.startswith("agent-browsing-"):
            server_name = "agent-browsing"
            actual_tool_name = tool_name[len("agent-browsing-") :]
            return server_name, actual_tool_name

        # 处理其他 agent-* 格式
        elif tool_name.startswith("agent-"):
            # 寻找最后一个 '-' 来分割server_name和tool_name
            last_dash = tool_name.rfind("-")
            if last_dash > 6:  # "agent-" 之后还有内容
                server_name = tool_name[:last_dash]
                actual_tool_name = tool_name[last_dash + 1 :]
            else:
                server_name = tool_name
                actual_tool_name = ""
            return server_name, actual_tool_name

        # 处理 tool-server_name-tool_name 格式
        elif tool_name.startswith("tool-"):
            parts = tool_name.split("-", 2)
            if len(parts) >= 3:
                server_name = parts[1]
                actual_tool_name = parts[2]
            else:
                server_name = "unknown"
                actual_tool_name = tool_name
            return server_name, actual_tool_name

        # 其他格式
        else:
            server_name = "unknown"
            actual_tool_name = tool_name
            return server_name, actual_tool_name

    # ==================== 基本信息 ====================

    def get_basic_info(self) -> Dict[str, Any]:
        """获取任务的基本信息"""
        return {
            "status": self.data.get("status"),
            "task_id": self.data.get("task_id"),
            "task_original_name": self.data.get("task_original_name"),
            "start_time": self.data.get("start_time"),
            "end_time": self.data.get("end_time"),
            "final_boxed_answer": self.data.get("final_boxed_answer"),
            "ground_truth": self.data.get("ground_truth"),
            "llm_as_judge_result": self.data.get("llm_as_judge_result"),
            "error": self.data.get("error", ""),
        }

    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要信息"""
        trace_data = self.data.get("trace_data", {})
        return trace_data.get("performance_summary", {})

    # ==================== 主代理消息历史 ====================

    def get_main_agent_history(self) -> Dict[str, Any]:
        """获取主代理的消息历史"""
        return self.data.get("main_agent_message_history", {})

    def get_main_agent_messages(self) -> List[Dict[str, Any]]:
        """获取主代理的消息列表"""
        history = self.get_main_agent_history()
        return history.get("message_history", [])

    # ==================== 浏览器代理消息历史 ====================

    def get_browser_agent_sessions(self) -> Dict[str, Any]:
        """获取所有浏览器代理会话"""
        # 尝试两种可能的键名
        browser_sessions = self.data.get("browser_agent_message_history_sessions", {})
        if not browser_sessions:
            browser_sessions = self.data.get("sub_agent_message_history_sessions", {})
        return browser_sessions

    def get_browser_agent_session_messages(
        self, session_id: str
    ) -> List[Dict[str, Any]]:
        """获取指定会话的消息列表"""
        sessions = self.get_browser_agent_sessions()
        session = sessions.get(session_id, {})
        return session.get("message_history", [])

    # ==================== MCP工具调用解析 ====================

    def parse_mcp_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """解析MCP工具调用"""
        pattern = r"<use_mcp_tool>\s*<server_name>(.*?)</server_name>\s*<tool_name>(.*?)</tool_name>\s*<arguments>\s*(.*?)\s*</arguments>\s*</use_mcp_tool>"

        match = re.search(pattern, text, re.DOTALL)
        if match:
            server_name = match.group(1).strip()
            tool_name = match.group(2).strip()
            arguments_str = match.group(3).strip()

            try:
                arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                arguments = arguments_str

            return {
                "server_name": server_name,
                "tool_name": tool_name,
                "arguments": arguments,
            }

        return None

    def extract_text_content(self, content) -> str:
        """提取消息内容中的文本"""
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    text_parts.append(item.get("text", ""))
            return "".join(text_parts)
        return str(content)

    def analyze_conversation_flow(self) -> List[Dict[str, Any]]:
        """分析对话流程，包括工具调用"""
        flow_steps = []
        main_messages = self.get_main_agent_messages()
        sub_agent_sessions = self.get_browser_agent_sessions()

        sub_agent_call_count = 0

        for i, message in enumerate(main_messages):
            role = message.get("role")
            content = message.get("content", [])

            text_content = self.extract_text_content(content)

            step = {
                "step_id": i,
                "agent": "main_agent",
                "role": role,
                "content_preview": text_content[:200] + "..."
                if len(text_content) > 200
                else text_content,
                "full_content": text_content,
                "tool_calls": [],
                "browser_session": None,
                "timestamp": message.get("timestamp", ""),
                "browser_flow": [],
            }

            # 如果是assistant消息，检查是否有工具调用
            if role == "assistant":
                # 检查新格式的tool_calls
                if "tool_calls" in message and message["tool_calls"]:
                    for tool_call in message["tool_calls"]:
                        # 转换新格式到统一格式
                        if "function" in tool_call:
                            function_info = tool_call["function"]
                            tool_name = function_info.get("name", "")
                            arguments = function_info.get("arguments", "")

                            # 解析arguments字符串为JSON（如果是字符串的话）
                            if isinstance(arguments, str):
                                try:
                                    arguments = json.loads(arguments)
                                except json.JSONDecodeError:
                                    pass

                            # 从tool_name中提取server_name（如果有的话）
                            server_name, actual_tool_name = (
                                self._parse_new_format_tool_name(tool_name)
                            )

                            parsed_tool_call = {
                                "server_name": server_name,
                                "tool_name": actual_tool_name,
                                "arguments": arguments,
                                "id": tool_call.get("id", ""),
                                "type": tool_call.get("type", "function"),
                                "format": "new",
                            }
                            step["tool_calls"].append(parsed_tool_call)

                            # 处理浏览器代理调用 - 与MCP格式保持完全一致的逻辑
                            if server_name.startswith("agent-"):
                                sub_agent_call_count += 1
                                session_id = f"{server_name}_{sub_agent_call_count}"
                                step["browser_session"] = session_id

                                # 分析browser session的对话流程
                                if session_id in sub_agent_sessions:
                                    browser_flow = self.analyze_browser_session_flow(
                                        session_id
                                    )
                                    step["browser_flow"] = browser_flow
                            elif server_name.startswith("browsing-agent"):
                                sub_agent_call_count += 1
                                session_id = f"browser_agent_{sub_agent_call_count}"
                                step["browser_session"] = session_id

                                # 分析browser session的对话流程
                                if session_id in sub_agent_sessions:
                                    browser_flow = self.analyze_browser_session_flow(
                                        session_id
                                    )
                                    step["browser_flow"] = browser_flow

                # 检查旧格式的MCP工具调用（保持兼容性）
                mcp_tool_call = self.parse_mcp_tool_call(text_content)
                if mcp_tool_call:
                    mcp_tool_call["format"] = "mcp"  # 标记为旧格式
                    step["tool_calls"].append(mcp_tool_call)

                    # 如果调用了browsing-agent，关联browser session
                    if mcp_tool_call["server_name"].startswith("agent-"):
                        sub_agent_call_count += 1
                        session_id = (
                            f"{mcp_tool_call['server_name']}_{sub_agent_call_count}"
                        )
                        step["browser_session"] = session_id

                        # 分析browser session的对话流程
                        if session_id in sub_agent_sessions:
                            browser_flow = self.analyze_browser_session_flow(session_id)
                            step["browser_flow"] = browser_flow
                    elif mcp_tool_call["server_name"].startswith("browsing-agent"):
                        sub_agent_call_count += 1
                        session_id = f"browser_agent_{sub_agent_call_count}"
                        step["browser_session"] = session_id

                        # 分析browser session的对话流程
                        if session_id in sub_agent_sessions:
                            browser_flow = self.analyze_browser_session_flow(session_id)
                            step["browser_flow"] = browser_flow
            flow_steps.append(step)

        return flow_steps

    def analyze_browser_session_flow(self, session_id: str) -> List[Dict[str, Any]]:
        """分析浏览器会话的对话流程"""
        browser_messages = self.get_browser_agent_session_messages(session_id)
        browser_flow = []

        for i, message in enumerate(browser_messages):
            role = message.get("role")
            content = message.get("content", [])

            text_content = self.extract_text_content(content)

            step = {
                "step_id": i,
                "agent": session_id,
                "role": role,
                "content_preview": text_content[:200] + "..."
                if len(text_content) > 200
                else text_content,
                "full_content": text_content,
                "tool_calls": [],
                "timestamp": message.get("timestamp", ""),
            }

            # 如果是assistant消息，检查是否有工具调用
            if role == "assistant":
                # 检查新格式的tool_calls
                if "tool_calls" in message and message["tool_calls"]:
                    for tool_call in message["tool_calls"]:
                        # 转换新格式到统一格式
                        if "function" in tool_call:
                            function_info = tool_call["function"]
                            tool_name = function_info.get("name", "")
                            arguments = function_info.get("arguments", "")

                            # 解析arguments字符串为JSON（如果是字符串的话）
                            if isinstance(arguments, str):
                                try:
                                    arguments = json.loads(arguments)
                                except json.JSONDecodeError:
                                    pass

                            # 从tool_name中提取server_name（如果有的话）
                            server_name, actual_tool_name = (
                                self._parse_new_format_tool_name(tool_name)
                            )

                            parsed_tool_call = {
                                "server_name": server_name,
                                "tool_name": actual_tool_name,
                                "arguments": arguments,
                                "id": tool_call.get("id", ""),
                                "type": tool_call.get("type", "function"),
                                "format": "new",
                            }
                            step["tool_calls"].append(parsed_tool_call)

                # 检查旧格式的MCP工具调用（保持兼容性）
                mcp_tool_call = self.parse_mcp_tool_call(text_content)
                if mcp_tool_call:
                    mcp_tool_call["format"] = "mcp"  # 标记为旧格式
                    step["tool_calls"].append(mcp_tool_call)

            browser_flow.append(step)

        return browser_flow

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取执行摘要信息"""
        flow_steps = self.analyze_conversation_flow()

        total_steps = len(flow_steps)
        tool_calls = []
        browser_sessions = []

        for step in flow_steps:
            if step["tool_calls"]:
                tool_calls.extend(step["tool_calls"])
            if step.get("browser_session"):
                browser_sessions.append(step["browser_session"])

            # 收集浏览器会话中的工具调用
            if step.get("browser_flow"):
                for browser_step in step["browser_flow"]:
                    if browser_step.get("tool_calls"):
                        tool_calls.extend(browser_step["tool_calls"])

        # 工具使用统计
        tool_usage = {}
        for tool in tool_calls:
            # 根据格式选择合适的键名生成方式
            if tool.get("format") == "new":
                # 新格式：使用server_name.tool_name，如果server_name是unknown则只用tool_name
                if tool.get("server_name") != "unknown":
                    key = f"{tool['server_name']}.{tool['tool_name']}"
                else:
                    key = tool["tool_name"]
            else:
                # 旧格式（MCP）：保持原有方式
                key = f"{tool['server_name']}.{tool['tool_name']}"
            tool_usage[key] = tool_usage.get(key, 0) + 1

        return {
            "total_steps": total_steps,
            "total_tool_calls": len(tool_calls),
            "browser_sessions_count": len(browser_sessions),
            "tool_usage_distribution": tool_usage,
            "browser_sessions": browser_sessions,
        }

    def get_spans_summary(self) -> Dict[str, Any]:
        """获取spans的统计摘要"""
        trace_data = self.data.get("trace_data", {})
        spans = trace_data.get("spans", [])

        agent_stats = {}
        for span in spans:
            agent = span.get("agent_context", "unknown")
            if agent not in agent_stats:
                agent_stats[agent] = {
                    "count": 0,
                    "total_duration": 0,
                    "span_types": set(),
                }
            agent_stats[agent]["count"] += 1
            agent_stats[agent]["total_duration"] += span.get("duration_seconds", 0)
            agent_stats[agent]["span_types"].add(span.get("name", "unknown"))

        # 转换set为list
        for agent in agent_stats:
            agent_stats[agent]["span_types"] = list(agent_stats[agent]["span_types"])

        return {
            "total_spans": len(spans),
            "total_duration": sum(span.get("duration_seconds", 0) for span in spans),
            "agent_stats": agent_stats,
        }

    def get_step_logs_summary(self) -> Dict[str, Any]:
        """获取步骤日志的摘要统计"""
        logs = self.data.get("step_logs", [])

        status_count = {}
        step_type_count = {}

        for log in logs:
            status = log.get("status", "unknown")
            step_name = log.get("step_name", "unknown")

            status_count[status] = status_count.get(status, 0) + 1
            step_type_count[step_name] = step_type_count.get(step_name, 0) + 1

        return {
            "total_logs": len(logs),
            "status_distribution": status_count,
            "step_type_distribution": step_type_count,
        }
