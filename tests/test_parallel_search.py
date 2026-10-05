# SPDX-FileCopyrightText: 2026 Parallel Web Systems Inc.
#
# SPDX-License-Identifier: Apache-2.0

"""Exercise the opt-in YAML -> stdio -> HTTP -> orchestrator path locally."""

import asyncio
import socket
import tempfile
import unittest
from pathlib import Path

import hydra
import uvicorn
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from sse_starlette.sse import AppStatus

from config import config_path
from src.core.orchestrator import Orchestrator
from src.core.pipeline import create_pipeline_components
from src.logging.task_tracer import TaskTracer
from src.tool.mcp_servers.parallel_search_mcp_server import USER_AGENT


class ScriptedClient:
    """Replace only model responses; discovery and tool calls remain real."""

    def reset_usage_stats(self):
        self.calls = 0
        self.results = []

    async def create_message(self, **kwargs):
        self.calls += 1
        tools = kwargs["tool_definitions"][0]["tools"]
        assert any(t["name"] == "search" for t in tools)
        if self.calls == 1:
            return "Searching documentation"
        assert self.results and "asyncio.run" in str(self.results)
        return r"asyncio.run executes a coroutine. Source: https://docs.python.org/3/library/asyncio-runner.html. \boxed{asyncio.run}"

    def process_llm_response(self, response, message_history, agent_type):
        message_history.append({"role": "assistant", "content": response})
        return response, self.calls > 1

    def extract_tool_calls_info(self, response, text):
        if self.calls == 1:
            return (
                [
                    {
                        "id": "search-1",
                        "server_name": "tool-searching-parallel",
                        "tool_name": "search",
                        "arguments": {"query": "asyncio.run"},
                    }
                ],
                [],
            )
        return ([], [])

    def update_message_history(self, history, results, exceeded):
        self.results.extend(results)
        history.append({"role": "user", "content": str(results)})
        return history

    def handle_max_turns_reached_summary_prompt(self, history, prompt):
        return prompt

    def get_usage_log(self):
        return "Scripted client; no language model API calls"


class ParallelSearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        AppStatus.should_exit_event = None
        self.requests = []
        backend = FastMCP("search-fixture")

        @backend.tool()
        def search(query: str) -> str:
            if query == "fail":
                raise ValueError("fixture search unavailable")
            return "asyncio.run executes a coroutine: https://docs.python.org/3/library/asyncio-runner.html"

        @backend.tool()
        def fetch(url: str) -> str:
            return "Fetched documentation: asyncio.run executes a coroutine."

        app = backend.http_app(transport="streamable-http")
        requests = self.requests

        class CaptureHeaders(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                requests.append(dict(request.headers))
                return await call_next(request)

        app.add_middleware(CaptureHeaders)
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        port = self.sock.getsockname()[1]
        self.server = uvicorn.Server(uvicorn.Config(app, log_level="error"))
        self.server_task = asyncio.create_task(self.server.serve(sockets=[self.sock]))
        for _ in range(100):
            if self.server.started:
                break
            await asyncio.sleep(0.01)
        self.assertTrue(self.server.started)
        with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
            self.cfg = hydra.compose(config_name="agent_quickstart_parallel_search")
        self.manager, self.subs, self.formatter = create_pipeline_components(self.cfg)
        params = self.manager.get_server_params("tool-searching-parallel")
        self.assertEqual(
            params.args, ["-m", "src.tool.mcp_servers.parallel_search_mcp_server"]
        )
        self.assertEqual(
            set(params.env), {"HTTPS_PROXY", "HTTP_PROXY", "NO_PROXY", "SSL_CERT_FILE"}
        )
        # Only substitute the remote endpoint, retaining the native loader and bridge.
        params.args = [
            "-c",
            "from src.tool.mcp_servers.parallel_search_mcp_server import create_server; "
            f'create_server("http://127.0.0.1:{port}/mcp").run(transport="stdio")',
        ]

    async def asyncTearDown(self):
        self.server.should_exit = True
        await self.server_task
        self.sock.close()

    async def test_discovery_execution_headers_and_exclusion(self):
        definitions = await self.manager.get_all_tool_definitions()
        self.assertEqual(
            {t["name"] for t in definitions[0]["tools"]}, {"search", "fetch"}
        )
        self.manager.tool_blacklist.add(("tool-searching-parallel", "fetch"))
        definitions = await self.manager.get_all_tool_definitions()
        self.assertEqual([t["name"] for t in definitions[0]["tools"]], ["search"])
        result = await self.manager.execute_tool_call(
            "tool-searching-parallel", "search", {"query": "asyncio.run"}
        )
        self.assertIn("https://docs.python.org/", result["result"])
        result = await self.manager.execute_tool_call(
            "tool-searching-parallel", "fetch", {"url": "https://docs.python.org/"}
        )
        self.assertIn("Fetched documentation", result["result"])
        self.assertTrue(self.requests)
        self.assertTrue(all(r["user-agent"] == USER_AGENT for r in self.requests))
        self.assertTrue(all("authorization" not in r for r in self.requests))

    async def test_errors_reach_existing_result_handling(self):
        result = await self.manager.execute_tool_call(
            "tool-searching-parallel", "search", {"query": "fail"}
        )
        self.assertIn("fixture search unavailable", str(result))
        result = await self.manager.execute_tool_call(
            "tool-searching-parallel", "search", {}
        )
        self.assertIn("query", str(result))

    async def test_orchestrator_final_answer_and_defaults(self):
        with hydra.initialize_config_dir(config_dir=config_path(), version_base=None):
            original = hydra.compose(config_name="agent_quickstart_search")
        self.assertEqual(
            list(original.main_agent.tool_config), ["tool-searching-serper"]
        )
        self.assertEqual(self.cfg.main_agent.llm, original.main_agent.llm)
        self.assertEqual(
            list(self.cfg.main_agent.tool_config), ["tool-searching-parallel"]
        )
        with tempfile.TemporaryDirectory() as directory:
            tracer = TaskTracer(
                log_path=Path(directory) / "task.log",
                task_name="fixture",
                task_id="fixture",
                ground_truth=None,
            )
            client = ScriptedClient()
            agent = Orchestrator(
                self.manager, self.subs, client, self.formatter, self.cfg, tracer
            )
            summary, answer = await agent.run_main_agent("What does asyncio.run do?")
            self.assertEqual(answer, "asyncio.run")
            self.assertIn("https://docs.python.org/", summary)
            self.assertTrue(client.results)


if __name__ == "__main__":
    unittest.main()
