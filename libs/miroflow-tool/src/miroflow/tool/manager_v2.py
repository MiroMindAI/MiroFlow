# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

from asyncio import Lock
from contextlib import AsyncExitStack
from enum import StrEnum
from typing import Any

from mcp import ClientSession, stdio_client
from mcp.types import TextContent
from miroflow.tool.manager import ToolManagerProtocol


class SandboxStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    STOPPED = "stopped"


class ToolSandboxWithStdio(ToolManagerProtocol):
    """a long-lived sandbox that keeps mcp stdio session alive.
    vs ToolManager:
    - ToolManager automatically open/close mcp session in calls to `get_all_tool_definitions()` and `execute_tool_call()`.
    - Here user manually open/close mcp session with `connect_to_server()` and `cleanup()`.
    """

    def __init__(self, server_configs: list[dict[str, Any]]):
        self.server_configs = server_configs
        self.lock = Lock()
        self.status = SandboxStatus.PENDING

        self.stack_by_server: dict[str, AsyncExitStack] = {}
        self.session_by_server: dict[str, ClientSession] = {}

    async def connect_to_server(self):
        # TODO: make sure this is only called ONCE PER AGENTIC LOOP.
        async with self.lock:
            if self.status != SandboxStatus.PENDING:
                return
            for config in self.server_configs:
                name = config["name"]
                params = config["params"]
                exit_stack = AsyncExitStack()
                stdio_transport = await exit_stack.enter_async_context(
                    stdio_client(params)
                )
                read, write = stdio_transport
                session = await exit_stack.enter_async_context(
                    ClientSession(read, write)
                )

                await session.initialize()
                self.stack_by_server[name] = exit_stack
                self.session_by_server[name] = session
            self.status = SandboxStatus.RUNNING

    async def cleanup(self):
        # TODO: make sure this is called ONCE PER AGENTIC LOOP
        async with self.lock:
            if self.status != SandboxStatus.RUNNING:
                return
            self.session_by_server.clear()
            for _, stack in self.stack_by_server.items():
                await stack.aclose()
            self.stack_by_server.clear()
            self.status = SandboxStatus.STOPPED

    async def get_all_tool_definitions(self) -> Any:
        """Retrieve all tool definitions from active sessions.
        Ensures that each session is valid before interacting with it."""

        def format_response(tool):
            return {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.inputSchema,
            }

        result = {}
        for name, session in self.session_by_server.items():
            result[name] = {"name": name, "tools": []}
            response = await session.list_tools()
            for tool in response.tools:
                formatted = format_response(tool)
                result[name]["tools"].append(formatted)
        return result

    async def execute_tool_call(self, *, server_name, tool_name, arguments) -> Any:
        session = self.session_by_server.get(server_name)
        if session is None:
            raise ValueError(
                f"Server '{server_name}' does not exist in session_by_server."
            )
        response = await session.call_tool(tool_name, arguments=arguments)
        content = response.content
        result = ""
        if len(content) > 0:
            last = content[-1]
            if isinstance(last, TextContent):
                result = last.text
        return {"server_name": server_name, "tool_name": tool_name, "result": result}
