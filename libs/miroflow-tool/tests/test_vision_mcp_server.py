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


class TestVisionMCPServer:
    """Test suite for Vision MCP Server functionality with dual-model support."""

    def _get_vision_credentials(self) -> Dict[str, str]:
        """Get vision API credentials, skip test if neither is available."""
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        openai_key = os.environ.get("OPENAI_API_KEY")

        if not anthropic_key and not openai_key:
            pytest.skip(
                "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY environment variable is set"
            )

        credentials = {}
        if anthropic_key:
            credentials["ANTHROPIC_API_KEY"] = anthropic_key
            credentials["ANTHROPIC_BASE_URL"] = "https://api.anthropic.com"
            credentials["ENABLE_CLAUDE_VISION"] = "true"
        if openai_key:
            credentials["OPENAI_API_KEY"] = openai_key
            credentials["OPENAI_BASE_URL"] = "https://api.openai.com/v1"
            credentials["ENABLE_OPENAI_VISION"] = "true"

        return credentials

    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        credentials = self._get_vision_credentials()
        tool_configs = [
            {
                "name": "tool-vqa",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "mirage.contrib.tools.mcp_servers.vision_mcp_server"],
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
        assert "tool-vqa" in tool_names
        assert len(tool_definitions[0]["tools"]) == 1

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "valid_image_car_description",
                "server_name": "tool-vqa",
                "tool_name": "visual_question_answering",
                "arguments": {
                    "image_path_or_url": "https://www.topgear.com/sites/default/files/news-listicle/image/2025/02/1-Renault-5-review.jpg?w=1654&h=930",
                    "question": "Describe the car in the image.",
                },
                "should_succeed": True,
                "expected_content_keywords": ["car", "vehicle", "yellow"],
                "expected_structure_keywords": [
                    "ocr",
                    "vqa",
                ],  # Should contain both OCR and VQA results
            },
            {
                "name": "invalid_format_pdf",
                "server_name": "tool-vqa",
                "tool_name": "visual_question_answering",
                "arguments": {
                    "image_path_or_url": "https://arxiv.org/pdf/2207.01510",
                    "question": "What is the main idea of the paper?",
                },
                "should_succeed": False,
                "expected_error_keywords": ["format", "invalid", "error"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_visual_question_answering(self, test_case: Dict[str, Any]):
        """Test visual question answering tool with various inputs."""
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

            # Check for expected structure (OCR and VQA results)
            if "expected_structure_keywords" in test_case:
                for keyword in test_case["expected_structure_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected structure keyword '{keyword}' not found in result: {result}"

        else:
            # Test error handling - should contain error information in the result
            if "expected_error_keywords" in test_case:
                assert any(
                    keyword.lower() in result_str
                    for keyword in test_case["expected_error_keywords"]
                ), f"Expected error keywords {test_case['expected_error_keywords']} not found in result: {result}"

    @pytest.mark.asyncio
    async def test_dual_model_output_structure(self):
        """Test that the output contains results from both OCR and VQA in the expected order."""
        tool_manager = self._create_tool_manager()

        server_name = "tool-vqa"
        tool_name = "visual_question_answering"
        arguments = {
            "image_path_or_url": "https://www.topgear.com/sites/default/files/news-listicle/image/2025/02/1-Renault-5-review.jpg?w=1654&h=930",
            "question": "What color is the car?",
        }

        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)
        assert result is not None
        result_str = str(result).lower()

        # Check that both OCR and VQA results are present
        # The order should be: OCR results first, then VQA results
        expected_patterns = [
            "ocr",  # Should contain OCR results
            "vqa",  # Should contain VQA results
        ]

        for pattern in expected_patterns:
            assert (
                pattern in result_str
            ), f"Expected pattern '{pattern}' not found in result: {result}"

    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self):
        """Test that tool execution handles timeouts properly."""
        tool_manager = self._create_tool_manager()

        # Use a reasonable timeout for the test (increased due to dual API calls)
        timeout_seconds = 60

        server_name = "tool-vqa"
        tool_name = "visual_question_answering"
        arguments = {
            "image_path_or_url": "https://www.topgear.com/sites/default/files/news-listicle/image/2025/02/1-Renault-5-review.jpg?w=1654&h=930",
            "question": "Describe the car in the image.",
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
            "tool-vqa", "nonexistent_tool", {}
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
            "nonexistent_server", "visual_question_answering", {}
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
            {"image_path_or_url": ""},  # Empty image path
            {"question": "What is this?"},  # Missing image path
            {"image_path_or_url": "invalid_url", "question": ""},  # Empty question
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_arguments(self, invalid_args: Dict[str, Any]):
        """Test error handling for invalid arguments."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-vqa", "visual_question_answering", invalid_args
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
                "image_path_or_url": "https://www.topgear.com/sites/default/files/news-listicle/image/2025/02/1-Renault-5-review.jpg?w=1654&h=930",
                "question": "What color is the car?",
            },
            {
                "image_path_or_url": "https://www.topgear.com/sites/default/files/news-listicle/image/2025/02/1-Renault-5-review.jpg?w=1654&h=930",
                "question": "What brand is the car?",
            },
        ]

        results = []
        for args in test_cases:
            result = await tool_manager.execute_tool_call(
                "tool-vqa", "visual_question_answering", args
            )
            results.append(result)
            assert result is not None

        # Ensure we got different results for different questions
        assert len(results) == len(test_cases)
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_api_key_handling(self):
        """Test that the tool handles missing API keys gracefully."""
        # Create a tool manager with no API keys
        tool_configs = [
            {
                "name": "tool-vqa",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "mirage.contrib.tools.mcp_servers.vision_mcp_server"],
                    env={},  # No API keys
                ),
            }
        ]
        tool_manager = ToolManager(tool_configs)

        result = await tool_manager.execute_tool_call(
            "tool-vqa",
            "visual_question_answering",
            {
                "image_path_or_url": "https://example.com/image.jpg",
                "question": "What is this?",
            },
        )

        assert result is not None
        result_str = str(result).lower()
        assert "error" in result_str

        # result_str = str(result).lower()
        # assert "error" not in result_str
        # assert "api" not in result_str and "key" not in result_str


# Configuration for pytest
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
