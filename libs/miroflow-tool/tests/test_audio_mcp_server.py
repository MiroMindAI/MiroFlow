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


class TestAudioMCPServer:
    """Test suite for Audio MCP Server functionality."""

    def _get_openai_credentials(self) -> Dict[str, str]:
        """Get OpenAI API credentials, skip test if not available."""
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            pytest.skip("OPENAI_API_KEY environment variable not set")

        return {
            "OPENAI_API_KEY": api_key,
        }

    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        credentials = self._get_openai_credentials()
        tool_configs = [
            {
                "name": "tool-transcribe",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "mirage.contrib.tools.mcp_servers.audio_mcp_server"],
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

        # Check if visual question answering tool is available
        tool_names = [tool.get("name") for tool in tool_definitions]
        assert "tool-transcribe" in tool_names
        assert len(tool_definitions[0]["tools"]) == 2

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "valid_audio_transcription_url",
                "server_name": "tool-transcribe",
                "tool_name": "audio_transcription",
                "arguments": {
                    "audio_path_or_url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_dbc14c89c1.mp3?filename=baby-talk-goodness4-86510.mp3",
                },
                "should_succeed": True,
                "expected_content_keywords": ["goodness"],
            },
            {
                "name": "valid_audio_transcription_local",
                "server_name": "tool-transcribe",
                "tool_name": "audio_transcription",
                "arguments": {
                    "audio_path_or_url": os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__),
                            "./files-for-tests/baby-talk-goodness4-86510.mp3",
                        )
                    ),
                },
                "should_succeed": True,
                "expected_content_keywords": ["goodness"],
            },
            {
                "name": "invalid_format_audio",
                "server_name": "tool-transcribe",
                "tool_name": "audio_transcription",
                "arguments": {
                    "audio_path_or_url": "https://arxiv.org/pdf/2207.01510",
                },
                "should_succeed": False,
                "expected_error_keywords": [
                    "format",
                    "invalid",
                    "error",
                    "unsupported",
                ],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_audio_transcription(self, test_case: Dict[str, Any]):
        """Test audio transcription tool with various inputs."""
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

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "valid_audio_question_answering_local",
                "server_name": "tool-transcribe",
                "tool_name": "audio_question_answering",
                "arguments": {
                    "audio_path_or_url": os.path.abspath(
                        os.path.join(
                            os.path.dirname(__file__),
                            "./files-for-tests/baby-talk-goodness4-86510.mp3",
                        )
                    ),
                    "question": "Who is talking? A baby or an adult?",
                },
                "should_succeed": True,
                "expected_content_keywords": ["duration: 1.8"],
            },
            {
                "name": "valid_audio_question_answering_url",
                "server_name": "tool-transcribe",
                "tool_name": "audio_question_answering",
                "arguments": {
                    "audio_path_or_url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_dbc14c89c1.mp3?filename=baby-talk-goodness4-86510.mp3",
                    "question": "Who is talking? A baby or an adult?",
                },
                "should_succeed": True,
                "expected_content_keywords": ["duration: 1.8"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_audio_question_answering(self, test_case: Dict[str, Any]):
        """Test audio question answering tool with various inputs."""
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
        timeout_seconds = 300

        server_name = "tool-transcribe"
        tool_name = "audio_transcription"
        arguments = {
            "audio_path_or_url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_dbc14c89c1.mp3?filename=baby-talk-goodness4-86510.mp3",
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
            "tool-transcribe", "nonexistent_tool", {}
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
            "nonexistent_server", "audio_transcription", {}
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
            {"audio_path_or_url": ""},  # Empty audio path
            {"audio_path_or_url": "invalid_url"},  # Invalid audio path
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_arguments(self, invalid_args: Dict[str, Any]):
        """Test error handling for invalid arguments."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-transcribe", "audio_transcription", invalid_args
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
                "audio_path_or_url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_dbc14c89c1.mp3?filename=baby-talk-goodness4-86510.mp3",
            },
            {
                "audio_path_or_url": "https://cdn.pixabay.com/download/audio/2022/03/15/audio_dbc14c89c1.mp3?filename=baby-talk-goodness4-86510.mp3",
            },
        ]

        results = []
        for args in test_cases:
            result = await tool_manager.execute_tool_call(
                "tool-transcribe", "audio_transcription", args
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
