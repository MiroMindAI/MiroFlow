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

current_file_path = os.path.abspath(__file__)
current_dir = os.path.dirname(current_file_path)
files_for_tests_dir = os.path.join(current_dir, "files-for-tests")
pytest.skip("Skipping all tests in this file", allow_module_level=True)


class TestReadingMCPServer:
    """Test suite for Reading MCP Server functionality."""

    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        tool_configs = [
            {
                "name": "reading-mcp-server",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "mirage.contrib.tools.mcp_servers.reading_mcp_server",
                    ],
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

        # Check if reading tools are available
        tool_names = [tool.get("name") for tool in tool_definitions]
        assert "reading-mcp-server" in tool_names

        # Check that we have the expected tools
        tools = tool_definitions[0]["tools"]
        expected_tools = ["convert_to_markdown"]
        available_tool_names = [tool["name"] for tool in tools]

        for expected_tool in expected_tools:
            assert (
                expected_tool in available_tool_names
            ), f"Tool {expected_tool} not found in available tools"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "convert_pdf_file",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": f"file://{files_for_tests_dir}/test-pdf.pdf",
                },
                "should_succeed": True,
                "expected_content_keywords": ["note-taking"],
            },
            {
                "name": "convert_excel_file",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": f"file://{files_for_tests_dir}/test-excel.xlsx",
                },
                "should_succeed": True,
                "expected_content_keywords": ["finance"],
            },
            {
                "name": "convert_word_file",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": f"file://{files_for_tests_dir}/test-word.docx",
                },
                "should_succeed": True,
                "expected_content_keywords": ["note-taking"],
            },
            {
                "name": "convert_powerpoint_file",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": f"file://{files_for_tests_dir}/test-ppt.pptx",
                },
                "should_succeed": True,
                "expected_content_keywords": ["computer system"],
            },
            {
                "name": "convert_image_file",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": f"file://{files_for_tests_dir}/test-zip.zip",
                },
                "should_succeed": True,
                "expected_content_keywords": [
                    "computer system",
                    "note-taking",
                    "finance",
                ],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_convert_to_markdown_valid_uris(self, test_case: Dict[str, Any]):
        """Test convert_to_markdown tool with valid URIs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"] and "expected_content_keywords" in test_case:
            for keyword in test_case["expected_content_keywords"]:
                assert (
                    keyword in result_str
                ), f"Expected keyword {keyword} not found in result: {result}"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "data_uri_text",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": "data:text/plain;base64,SGVsbG8gV29ybGQ=",
                },
                "should_succeed": True,
            },
            {
                "name": "data_uri_html",
                "server_name": "reading-mcp-server",
                "tool_name": "convert_to_markdown",
                "arguments": {
                    "uri": "data:text/html,<h1>Hello World</h1>",
                },
                "should_succeed": True,
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_data_uri_convert_to_markdown(self, test_case: Dict[str, Any]):
        """Test convert_to_markdown tool with file and data URIs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()
        # Note: Results may vary depending on markitdown-mcp server availability
        # We mainly test that the call doesn't crash and returns some response
        assert "hello world" in result_str, f"Incorrect result in result: {result}"

    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self):
        """Test that tool execution handles timeouts properly."""
        tool_manager = self._create_tool_manager()

        timeout_seconds = 120

        server_name = "reading-mcp-server"
        tool_name = "convert_to_markdown"
        arguments = {
            "uri": f"file://{files_for_tests_dir}/test-pdf.pdf",
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
            assert "error" not in result_str, f"Unexpected error in result: {result}"
        except asyncio.TimeoutError:
            pytest.fail(f"Tool execution timed out after {timeout_seconds} seconds")

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test error handling for invalid tool names."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "reading-mcp-server", "nonexistent_tool", {}
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
            "nonexistent_server",
            "convert_to_markdown",
            {"uri": f"file://{files_for_tests_dir}/test-pdf.pdf"},
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
            {},  # Missing required uri argument
            {
                "wrong_param": f"file://{files_for_tests_dir}/test-pdf.pdf"
            },  # Wrong parameter name
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_arguments(self, invalid_args: Dict[str, Any]):
        """Test error handling for invalid arguments."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "reading-mcp-server", "convert_to_markdown", invalid_args
        )

        assert result is not None
        result_str = str(result).lower()
        # Should contain error information about invalid arguments
        error_indicators = ["error", "invalid", "missing", "required"]
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
                "tool_name": "convert_to_markdown",
                "arguments": {"uri": f"file://{files_for_tests_dir}/test-word.docx"},
            },
            {
                "tool_name": "convert_to_markdown",
                "arguments": {"uri": f"file://{files_for_tests_dir}/test-pdf.pdf"},
            },
            {
                "tool_name": "convert_to_markdown",
                "arguments": {"uri": "data:text/plain,Hello World"},
            },
        ]

        results = []
        for test_case in test_cases:
            result = await tool_manager.execute_tool_call(
                "reading-mcp-server", test_case["tool_name"], test_case["arguments"]
            )
            results.append(result)
            assert result is not None

        # Ensure we got results for all calls
        assert len(results) == len(test_cases)
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_uri_scheme_validation(self):
        """Test that URI scheme validation works correctly."""
        tool_manager = self._create_tool_manager()

        # Test invalid schemes
        invalid_schemes = ["ftp:", "smtp:", "custom:", ""]
        for scheme in invalid_schemes:
            if scheme:
                test_uri = f"{scheme}//example.com"
            else:
                test_uri = "example.com"

            result = await tool_manager.execute_tool_call(
                "reading-mcp-server",
                "convert_to_markdown",
                {"uri": test_uri},
            )
            assert result is not None
            result_str = str(result).lower()
            # Should contain scheme validation error
            assert "error" in result_str and (
                "invalid" in result_str or "scheme" in result_str
            )


# Configuration for pytest
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
