# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import functools
from typing import Any, Awaitable, Callable, Protocol, TypeVar

from mcp import ClientSession, StdioServerParameters  # (已在 config.py 导入)
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client

from .logger import bootstrap_logger
from .mcp_servers.browser_session import PlaywrightSession

logger = bootstrap_logger()

R = TypeVar("R")


def with_timeout(timeout_s: float = 300.0):
    """
    Decorator: wraps any *async* function in asyncio.wait_for().
    Usage:
        @with_timeout(20)
        async def create_message_foo(...): ...
    """

    def decorator(
        func: Callable[..., Awaitable[R]],
    ) -> Callable[..., Awaitable[R]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> R:
            return await asyncio.wait_for(func(*args, **kwargs), timeout=timeout_s)

        return wrapper

    return decorator


class ToolManagerProtocol(Protocol):
    """this enables other kinds of tool manager."""

    async def get_all_tool_definitions(self) -> Any: ...
    async def execute_tool_call(
        self, *, server_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any: ...


class ToolManager(ToolManagerProtocol):
    def __init__(self, server_configs, tool_blacklist=None):
        """
        初始化 ToolManager。
        :param server_configs: create_server_parameters() 返回的列表
        """
        self.server_configs = server_configs
        self.server_dict = {
            config["name"]: config["params"] for config in server_configs
        }
        self.browser_session = None
        self.tool_blacklist = tool_blacklist if tool_blacklist else set()

        logger.info(
            f"ToolManager 初始化，已加载服务器: {list(self.server_dict.keys())}"
        )

    def _is_huggingface_dataset_or_space_url(self, url):
        """
        Check if the URL is a Hugging Face dataset or space URL.
        :param url: The URL to check
        :return: True if it's a HuggingFace dataset or space URL, False otherwise
        """
        if not url:
            return False
        return "huggingface.co/datasets" in url or "huggingface.co/spaces" in url

    def _should_block_hf_scraping(self, tool_name, arguments):
        """
        Check if we should block scraping of Hugging Face datasets/spaces.
        :param tool_name: The name of the tool being called
        :param arguments: The arguments passed to the tool
        :return: True if scraping should be blocked, False otherwise
        """
        return (
            tool_name == "scrape"
            and arguments.get("url")
            and self._is_huggingface_dataset_or_space_url(arguments["url"])
        )

    def get_server_params(self, server_name):
        """获取指定服务器的参数"""
        return self.server_dict.get(server_name)

    async def _find_servers_with_tool(self, tool_name):
        """
        在所有服务器中查找包含指定工具名称的服务器
        :param tool_name: 要查找的工具名称
        :return: 包含该工具的服务器名称列表
        """
        servers_with_tool = []

        for config in self.server_configs:
            server_name = config["name"]
            server_params = config["params"]

            try:
                if isinstance(server_params, StdioServerParameters):
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(
                            read, write, sampling_callback=None
                        ) as session:
                            await session.initialize()
                            tools_response = await session.list_tools()
                            # 遵循与 get_all_tool_definitions 相同的 blacklist 逻辑
                            for tool in tools_response.tools:
                                if (server_name, tool.name) in self.tool_blacklist:
                                    continue
                                if tool.name == tool_name:
                                    servers_with_tool.append(server_name)
                                    break
                elif isinstance(server_params, str) and server_params.startswith(
                    ("http://", "https://")
                ):
                    # SSE endpoint
                    async with sse_client(server_params) as (read, write):
                        async with ClientSession(
                            read, write, sampling_callback=None
                        ) as session:
                            await session.initialize()
                            tools_response = await session.list_tools()
                            for tool in tools_response.tools:
                                # 与 get_all_tool_definitions 保持一致：SSE 部分没有 blacklist 处理
                                # 可以在这里添加特定工具的过滤逻辑（如果需要）
                                # if server_name == "tool-excel" and tool.name not in ["get_workbook_metadata", "read_data_from_excel"]:
                                #     continue
                                if tool.name == tool_name:
                                    servers_with_tool.append(server_name)
                                    break
                else:
                    logger.error(
                        f"错误: 服务器 '{server_name}' 的参数类型未知: {type(server_params)}"
                    )
                    # 对于未知类型，我们跳过而不是抛出异常，因为这是查找功能
                    continue
            except Exception as e:
                logger.error(
                    f"错误: 无法连接或获取服务器 '{server_name}' 的工具以查找 '{tool_name}': {e}"
                )
                continue

        return servers_with_tool

    async def get_all_tool_definitions(self):
        """
        连接到所有已配置的服务器，获取它们的工具定义。
        返回一个适合传递给 Prompt 生成器的列表。
        """
        all_servers_for_prompt = []
        # 处理远程服务器工具
        for config in self.server_configs:
            server_name = config["name"]
            server_params = config["params"]
            one_server_for_prompt = {"name": server_name, "tools": []}
            logger.info(f"正在获取服务器 '{server_name}' 的工具定义...")

            try:
                if isinstance(server_params, StdioServerParameters):
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(
                            read, write, sampling_callback=None
                        ) as session:
                            await session.initialize()
                            tools_response = await session.list_tools()
                            # black list some tools
                            for tool in tools_response.tools:
                                if (server_name, tool.name) in self.tool_blacklist:
                                    logger.info(
                                        f"server '{server_name}' 中的工具 '{tool.name}' 被列入黑名单，跳过。"
                                    )
                                    continue
                                one_server_for_prompt["tools"].append(
                                    {
                                        "name": tool.name,
                                        "description": tool.description,
                                        "schema": tool.inputSchema,
                                    }
                                )
                elif isinstance(server_params, str) and server_params.startswith(
                    ("http://", "https://")
                ):
                    # SSE endpoint
                    async with sse_client(server_params) as (read, write):
                        async with ClientSession(
                            read, write, sampling_callback=None
                        ) as session:
                            await session.initialize()
                            tools_response = await session.list_tools()
                            for tool in tools_response.tools:
                                # 可以在这里添加特定工具的过滤逻辑（如果需要）
                                # if server_name == "tool-excel" and tool.name not in ["get_workbook_metadata", "read_data_from_excel"]:
                                #     continue
                                one_server_for_prompt["tools"].append(
                                    {
                                        "name": tool.name,
                                        "description": tool.description,
                                        "schema": tool.inputSchema,
                                    }
                                )
                else:
                    logger.error(
                        f"错误: 服务器 '{server_name}' 的参数类型未知: {type(server_params)}"
                    )
                    raise TypeError(
                        f"Unknown server params type for {server_name}: {type(server_params)}"
                    )

                logger.info(
                    f"成功获取服务器 '{server_name}' 的 {len(one_server_for_prompt['tools'])} 个工具定义。"
                )
                all_servers_for_prompt.append(one_server_for_prompt)

            except Exception as e:
                logger.error(f"错误: 无法连接或获取服务器 '{server_name}' 的工具: {e}")
                # 仍然添加服务器条目，但标记工具列表为空或包含错误信息
                one_server_for_prompt["tools"] = [
                    {"error": f"Failed to fetch tools: {e}"}
                ]
                all_servers_for_prompt.append(one_server_for_prompt)

        return all_servers_for_prompt

    @with_timeout(600)
    async def execute_tool_call(self, server_name, tool_name, arguments) -> Any:
        """
        执行单个工具调用。
        :param server_name: 服务器名称
        :param tool_name: 工具名称
        :param arguments: 工具参数字典
        :return: 包含结果或错误的字典
        """

        # 原远程服务器调用逻辑
        server_params = self.get_server_params(server_name)
        if not server_params:
            logger.error(f"错误: 尝试调用未找到的服务器 '{server_name}'")
            return {
                "server_name": server_name,
                "tool_name": tool_name,
                "error": f"Server '{server_name}' not found.",
            }

        logger.info(
            f"正在连接到服务器 '{server_name}' 以调用工具 '{tool_name}'...调用参数为'{arguments}'..."
        )

        if server_name == "playwright":
            try:
                if self.browser_session is None:
                    self.browser_session = PlaywrightSession(server_params)
                    await self.browser_session.connect()
                tool_result = await self.browser_session.call_tool(
                    tool_name, arguments=arguments
                )

                # 检查结果是否为空并提供更好的反馈
                if tool_result is None or tool_result == "":
                    logger.error(
                        f"工具 '{tool_name}' 返回了空结果，可能是正常的（如删除操作）或工具执行有问题"
                    )
                    return {
                        "server_name": server_name,
                        "tool_name": tool_name,
                        "result": f"Tool '{tool_name}' returned empty result - this may be expected (e.g., delete operations) or indicate an issue with tool execution",
                    }

                return {
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "result": tool_result,
                }
            except Exception as e:
                return {
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "error": f"Tool call failed: {str(e)}",
                }
        else:
            try:
                result_content = None
                if isinstance(server_params, StdioServerParameters):
                    async with stdio_client(server_params) as (read, write):
                        async with ClientSession(
                            read, write, sampling_callback=None
                        ) as session:
                            await session.initialize()
                            try:
                                tool_result = await session.call_tool(
                                    tool_name, arguments=arguments
                                )
                                # 安全地提取结果内容，不改变原始格式
                                if tool_result.content and len(tool_result.content) > 0:
                                    text_content = tool_result.content[-1].text
                                    if (
                                        text_content is not None
                                        and text_content.strip()
                                    ):
                                        result_content = text_content  # 保留原始格式！
                                    else:
                                        result_content = f"Tool '{tool_name}' completed but returned empty text - this may be expected or indicate an issue"
                                else:
                                    result_content = f"Tool '{tool_name}' completed but returned no content - this may be expected or indicate an issue"

                                # 如果结果为空，记录警告
                                if not tool_result.content:
                                    logger.error(
                                        f"工具 '{tool_name}' 返回了空内容，tool_result.content: {tool_result.content}"
                                    )

                                # post hoc check for browsing agent reading answers from hf datsets
                                if self._should_block_hf_scraping(tool_name, arguments):
                                    result_content = "You are trying to scrape a Hugging Face dataset for answers, please do not use the scrape tool for this purpose."
                            except Exception as tool_error:
                                logger.error(f"Tool execution error: {tool_error}")
                                return {
                                    "server_name": server_name,
                                    "tool_name": tool_name,
                                    "error": f"Tool execution failed: {str(tool_error)}",
                                }
                elif isinstance(server_params, str) and server_params.startswith(
                    ("http://", "https://")
                ):
                    async with sse_client(server_params) as (read, write):
                        async with ClientSession(
                            read, write, sampling_callback=None
                        ) as session:
                            await session.initialize()
                            try:
                                tool_result = await session.call_tool(
                                    tool_name, arguments=arguments
                                )
                                # 安全地提取结果内容，不改变原始格式
                                if tool_result.content and len(tool_result.content) > 0:
                                    text_content = tool_result.content[-1].text
                                    if (
                                        text_content is not None
                                        and text_content.strip()
                                    ):
                                        result_content = text_content  # 保留原始格式！
                                    else:
                                        result_content = f"Tool '{tool_name}' completed but returned empty text - this may be expected or indicate an issue"
                                else:
                                    result_content = f"Tool '{tool_name}' completed but returned no content - this may be expected or indicate an issue"

                                # 如果结果为空，记录警告
                                if not tool_result.content:
                                    logger.error(
                                        f"工具 '{tool_name}' 返回了空内容，tool_result.content: {tool_result.content}"
                                    )

                                # post hoc check for browsing agent reading answers from hf datsets
                                if self._should_block_hf_scraping(tool_name, arguments):
                                    result_content = "You are trying to scrape a Hugging Face dataset for answers, please do not use the scrape tool for this purpose."
                            except Exception as tool_error:
                                logger.error(f"Tool execution error: {tool_error}")
                                return {
                                    "server_name": server_name,
                                    "tool_name": tool_name,
                                    "error": f"Tool execution failed: {str(tool_error)}",
                                }
                else:
                    raise TypeError(
                        f"Unknown server params type for {server_name}: {type(server_params)}"
                    )

                logger.info(f"工具 '{tool_name}' (服务器: '{server_name}') 调用成功。")

                return {
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "result": result_content,  # 返回提取的文本内容
                }

            except Exception as outer_e:  # Rename this to outer_e to avoid shadowing
                logger.error(
                    f"错误: 调用工具 '{tool_name}' (服务器: '{server_name}') 失败: {outer_e}"
                )
                # import traceback
                # traceback.print_exc() # 打印详细堆栈跟踪以进行调试

                # Store the original error message for later use
                error_message = str(outer_e)

                if (
                    tool_name == "scrape"
                    and "unhandled errors" in error_message
                    and "url" in arguments
                    and arguments["url"] is not None
                ):
                    try:
                        logger.info("尝试使用 MarkItDown 进行回退...")
                        from markitdown import MarkItDown

                        md = MarkItDown(
                            docintel_endpoint="<document_intelligence_endpoint>"
                        )
                        result = md.convert(arguments["url"])
                        logger.info("使用 MarkItDown 成功")
                        return {
                            "server_name": server_name,
                            "tool_name": tool_name,
                            "result": result.text_content,  # 返回提取的文本内容
                        }
                    except (
                        Exception
                    ) as inner_e:  # Use a different name to avoid shadowing
                        # Log the inner exception if needed
                        logger.error(f"Fallback also failed: {inner_e}")
                        # No need for pass here as we'll continue to the return statement

                # Always use the outer exception for the final error response
                return {
                    "server_name": server_name,
                    "tool_name": tool_name,
                    "error": f"Tool call failed: {error_message}",
                }
