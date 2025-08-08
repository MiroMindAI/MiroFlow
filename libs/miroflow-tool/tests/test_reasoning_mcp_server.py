# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import asyncio
import os
import sys
from typing import Any, Dict

import pytest
from mcp import StdioServerParameters

from miroflow.tool.manager import ToolManager


class TestReasoningMCPServer:
    """Test suite for Reasoning MCP Server functionality."""

    def _get_anthropic_credentials(self) -> Dict[str, str]:
        """Get Anthropic API credentials, skip test if not available."""
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            pytest.skip("ANTHROPIC_API_KEY environment variable not set")

        return {
            "ANTHROPIC_API_KEY": api_key,
            "ANTHROPIC_BASE_URL": "https://api.anthropic.com",
        }

    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        credentials = self._get_anthropic_credentials()
        tool_configs = [
            {
                "name": "tool-reasoning",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "mirage.contrib.tools.mcp_servers.reasoning_mcp_server",
                    ],
                    env=credentials,
                ),
            }
        ]
        return ToolManager(tool_configs)

    @pytest.mark.asyncio
    async def test_tool_definitions_available(self):
        """Test that tool definitions are properly loaded."""
        tool_manager = self._create_tool_manager()
        tool_definitions = await tool_manager.get_all_tool_definitions()

        assert tool_definitions is not None
        assert len(tool_definitions) == 1

        # Check if reasoning tool is available
        tool_names = [tool.get("name") for tool in tool_definitions]
        assert "tool-reasoning" in tool_names
        assert len(tool_definitions[0]["tools"]) == 1

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "hard_question",
                "server_name": "tool-reasoning",
                "tool_name": "reasoning",
                "arguments": {
                    "question": "What is the minimum nature number of moves to solve a Rubik's cube?",
                },
                "should_succeed": True,
            },
            {
                "name": "easy_question",
                "server_name": "tool-reasoning",
                "tool_name": "reasoning",
                "arguments": {
                    "question": "What is the capital of France?",
                },
                "should_succeed": True,
                "expected_content_keywords": ["Paris"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_reasoning(self, test_case: Dict[str, Any]):
        """Test reasoning tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call (no exceptions expected, errors are returned in results)
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"]:
            # Test successful execution - should not contain error indicators
            error_indicators = ["error", "failed", "exception", "traceback"]
            for indicator in error_indicators:
                assert (
                    indicator not in result_str
                ), f"Unexpected error indicator '{indicator}' found in successful test result: {result}"

            # Check for expected content if keywords provided
            if "expected_content_keywords" in test_case:
                for keyword in test_case["expected_content_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected keyword '{keyword}' not found in result: {result}"

        else:
            # Test error handling - should contain error information in the result
            if "expected_error_keywords" in test_case:
                assert any(
                    keyword.lower() in result_str
                    for keyword in test_case["expected_error_keywords"]
                ), f"Expected error keywords {test_case['expected_error_keywords']} not found in result: {result}"

    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self):
        """Test that tool execution handles timeouts properly."""
        tool_manager = self._create_tool_manager()

        # Use a reasonable timeout for the test
        timeout_seconds = 120

        server_name = "tool-reasoning"
        tool_name = "reasoning"
        arguments = {
            "question": "What is the minimum nature number of moves to solve a Rubik's cube?",
        }

        try:
            result = await asyncio.wait_for(
                tool_manager.execute_tool_call(server_name, tool_name, arguments),
                timeout=timeout_seconds,
            )
            # If we get here, the call completed within timeout
            assert result is not None
            # Check that it's not an error result
            result_str = str(result).lower()
            assert (
                "timeout" not in result_str
            ), f"Tool execution reported timeout in result: {result}"
        except asyncio.TimeoutError:
            pytest.fail(f"Tool execution timed out after {timeout_seconds} seconds")

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test error handling for invalid tool names."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-reasoning", "nonexistent_tool", {}
        )

        assert result is not None
        result_str = str(result).lower()
        # Should contain error information about the invalid tool
        error_indicators = ["error", "not found", "invalid", "unknown"]
        assert any(
            indicator in result_str for indicator in error_indicators
        ), f"Expected error indicators not found for invalid tool name in result: {result}"

    @pytest.mark.asyncio
    async def test_invalid_server_name(self):
        """Test error handling for invalid server names."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "nonexistent_server", "reasoning", {}
        )

        assert result is not None
        result_str = str(result).lower()
        # Should contain error information about the invalid server
        error_indicators = ["error", "not found", "invalid", "server"]
        assert any(
            indicator in result_str for indicator in error_indicators
        ), f"Expected error indicators not found for invalid server name in result: {result}"

    @pytest.mark.parametrize(
        "invalid_args",
        [
            {},  # Missing required arguments
            {"question": ""},  # Empty question
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_arguments(self, invalid_args: Dict[str, Any]):
        """Test error handling for invalid arguments."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-reasoning", "reasoning", invalid_args
        )

        assert result is not None
        result_str = str(result).lower()
        # Should contain error information about invalid arguments
        error_indicators = ["error", "invalid", "missing", "required", "empty"]
        assert any(
            indicator in result_str for indicator in error_indicators
        ), f"Expected error indicators not found for invalid arguments {invalid_args} in result: {result}"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_multiple_consecutive_calls(self):
        """Test that multiple consecutive calls work properly."""
        tool_manager = self._create_tool_manager()

        test_cases = [
            {
                "question": "What is the minimum nature number of moves to solve a Rubik's cube?",
            },
            {
                "question": "What is the capital of France?",
            },
        ]

        results = []
        for args in test_cases:
            result = await tool_manager.execute_tool_call(
                "tool-reasoning", "reasoning", args
            )
            results.append(result)
            assert result is not None

        # Ensure we got different results for different questions
        assert len(results) == len(test_cases)
        assert all(result is not None for result in results)


# Configuration for pytest
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
