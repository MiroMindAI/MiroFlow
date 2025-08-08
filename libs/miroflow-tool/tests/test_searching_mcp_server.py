import asyncio
import os
import sys
from typing import Any, Dict

import pytest
from mcp import StdioServerParameters

from miroflow.tool.manager import ToolManager

pytest.skip("Skipping all tests in this file", allow_module_level=True)


class TestSearchingMCPServer:
    """Test suite for Searching MCP Server functionality."""

    def _get_credentials(self) -> Dict[str, str]:
        """Get Serper API credentials, skip test if not available."""
        serper_api_key = os.environ.get("SERPER_API_KEY")
        jina_api_key = os.environ.get("JINA_API_KEY")
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        if not serper_api_key or not jina_api_key or not gemini_api_key:
            pytest.skip(
                "SERPER_API_KEY or JINA_API_KEY or GEMINI_API_KEY environment variable not set"
            )

        return {
            "SERPER_API_KEY": serper_api_key,
            "JINA_API_KEY": jina_api_key,
            "GEMINI_API_KEY": gemini_api_key,
        }

    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        credentials = self._get_credentials()
        tool_configs = [
            {
                "name": "searching-mcp-server",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "mirage.contrib.tools.mcp_servers.searching_mcp_server",
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

        # Check if searching tools are available
        tool_names = [tool.get("name") for tool in tool_definitions]
        assert "searching-mcp-server" in tool_names

        # Check that we have the expected tools
        tools = tool_definitions[0]["tools"]
        expected_tools = [
            "google_search",
            "wiki_search",
            "wiki_search_revision",
            "search_archived_webpage",
            "scrape_website",
            "ask_youtube_video",
        ]
        available_tool_names = [tool["name"] for tool in tools]

        for expected_tool in expected_tools:
            assert (
                expected_tool in available_tool_names
            ), f"Tool {expected_tool} not found in available tools"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "google_search_basic",
                "server_name": "searching-mcp-server",
                "tool_name": "google_search",
                "arguments": {
                    "q": "What is the capital of France?",
                    "gl": "us",
                    "hl": "en",
                    "location": "California, United States",
                    "num": 5,
                    "page": 1,
                },
                "should_succeed": True,
                "expected_content_keywords": ["Paris"],
            },
            {
                "name": "google_search_with_location",
                "server_name": "searching-mcp-server",
                "tool_name": "google_search",
                "arguments": {
                    "q": "best restaurants",
                    "location": "New York, United States",
                    "num": 5,
                },
                "should_succeed": True,
                "expected_content_keywords": ["New York"],
            },
            {
                "name": "google_search_with_time_filter",
                "server_name": "searching-mcp-server",
                "tool_name": "google_search",
                "arguments": {
                    "q": "latest news",
                    "gl": "us",
                    "hl": "en",
                    "tbs": "qdr:d",  # past day
                },
                "should_succeed": True,
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_google_search(self, test_case: Dict[str, Any]):
        """Test google_search tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
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

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "wiki_search_entity",
                "server_name": "searching-mcp-server",
                "tool_name": "wiki_get_page_content",
                "arguments": {
                    "entity": "Paris",
                    "summary_sentences": 5,
                },
                "should_succeed": True,
                "expected_content_keywords": ["Paris", "France", "capital"],
            },
            {
                "name": "wiki_search_full_content",
                "server_name": "searching-mcp-server",
                "tool_name": "wiki_get_page_content",
                "arguments": {
                    "entity": "Python programming language",
                    "summary_sentences": 0,  # Full content
                },
                "should_succeed": True,
                "expected_content_keywords": [
                    "high-level",
                    "https://en.wikipedia.org/wiki/Python_(programming_language)",
                ],
            },
            {
                "name": "wiki_search_nonexistent",
                "server_name": "searching-mcp-server",
                "tool_name": "wiki_get_page_content",
                "arguments": {
                    "entity": "NonexistentEntityThatDoesNotExist123456",
                },
                "should_succeed": True,  # Should succeed but return "not found" message
                "expected_content_keywords": ["Page Not Found"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_wiki_search(self, test_case: Dict[str, Any]):
        """Test wiki_search tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"]:
            # Check for expected content if keywords provided
            if "expected_content_keywords" in test_case:
                for keyword in test_case["expected_content_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected keyword '{keyword}' not found in result: {result}"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "wiki_search_revision_valid",
                "server_name": "searching-mcp-server",
                "tool_name": "search_wiki_revision",
                "arguments": {
                    "entity": "Paris",
                    "year": 2020,
                    "month": 1,
                    "max_revisions": 10,
                },
                "should_succeed": True,
                "expected_content_keywords": [
                    "Revision Period: 2020-01",
                    "Revision ID: 933446542",
                ],
            },
            # {
            #     "name": "wiki_search_revision_invalid_month",
            #     "server_name": "searching-mcp-server",
            #     "tool_name": "search_wiki_revision",
            #     "arguments": {
            #         "entity": "Paris",
            #         "year": 2024,
            #         "month": 13,  # Invalid month
            #     },
            #     "should_succeed": True,  # Should succeed but return error message
            #     "expected_content_keywords": ["invalid month"],
            # },
            {
                "name": "wiki_search_revision_invalid_year",
                "server_name": "searching-mcp-server",
                "tool_name": "search_wiki_revision",
                "arguments": {
                    "entity": "Paris",
                    "year": 1999,  # Before Wikipedia
                    "month": 1,
                },
                "should_succeed": True,  # Should succeed but return error message
                "expected_content_keywords": ["invalid year"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_wiki_search_revision(self, test_case: Dict[str, Any]):
        """Test wiki_search_revision tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"]:
            # Check for expected content if keywords provided
            if "expected_content_keywords" in test_case:
                for keyword in test_case["expected_content_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected keyword '{keyword}' not found in result: {result}"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "search_archived_webpage_with_date",
                "server_name": "searching-mcp-server",
                "tool_name": "search_archived_webpage",
                "arguments": {
                    "url": "https://www.apple.com/",
                    "date": "20240102",
                },
                "should_succeed": True,
                "expected_content_keywords": ["https://www.apple.com/"],
            },
            {
                "name": "search_archived_webpage_with_date",
                "server_name": "searching-mcp-server",
                "tool_name": "search_archived_webpage",
                "arguments": {
                    "url": "https://www.apple.com/",
                    "date": "20240101",
                },
                "should_succeed": True,
                "expected_content_keywords": ["https://www.apple.com/"],
            },
            {
                "name": "search_archived_webpage_invalid_url",
                "server_name": "searching-mcp-server",
                "tool_name": "search_archived_webpage",
                "arguments": {
                    "url": "not-a-valid-url",
                },
                "should_succeed": True,  # Should succeed but return error message
                "expected_content_keywords": ["invalid url"],
            },
            {
                "name": "search_archived_webpage_invalid_date",
                "server_name": "searching-mcp-server",
                "tool_name": "search_archived_webpage",
                "arguments": {
                    "url": "https://www.google.com/",
                    "date": "18041209",
                },
                "should_succeed": True,  # Should succeed but return error message
                "expected_content_keywords": ["invalid"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_search_archived_webpage(self, test_case: Dict[str, Any]):
        """Test search_archived_webpage tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"]:
            # Check for expected content if keywords provided
            if "expected_content_keywords" in test_case:
                for keyword in test_case["expected_content_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected keyword '{keyword}' not found in result: {result}"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "scrape_website_normal",
                "server_name": "searching-mcp-server",
                "tool_name": "scrape_website",
                "arguments": {
                    "url": "http://web.archive.org/web/20240102235850/https://www.apple.com/",
                },
                "should_succeed": True,
                "expected_content_keywords": ["iPhone 15"],
            },
            {
                "name": "scrape_website_huggingface_blocked",
                "server_name": "searching-mcp-server",
                "tool_name": "scrape_website",
                "arguments": {
                    "url": "https://huggingface.co/datasets/miromind-ai/",
                },
                "should_succeed": True,  # Should succeed but return blocking message
                "expected_content_keywords": ["please do not"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_scrape_website(self, test_case: Dict[str, Any]):
        """Test scrape_website tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"]:
            # Check for expected content if keywords provided
            if "expected_content_keywords" in test_case:
                for keyword in test_case["expected_content_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected keyword '{keyword}' not found in result: {result}"

    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "ask_youtube_video_normal",
                "server_name": "searching-mcp-server",
                "tool_name": "ask_youtube_video",
                "arguments": {
                    "url": "https://www.youtube.com/watch?v=t7AtQHXCW5s",
                    "question": "How many white letter 'E's are in the top red area at 30 seconds of the video?",
                },
                "should_succeed": True,
                "expected_content_keywords": ["4", "Hint: "],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_ask_youtube_video(self, test_case: Dict[str, Any]):
        """Test ask_youtube_video tool with various inputs."""
        tool_manager = self._create_tool_manager()

        server_name = test_case["server_name"]
        tool_name = test_case["tool_name"]
        arguments = test_case["arguments"]

        # Execute the tool call
        result = await tool_manager.execute_tool_call(server_name, tool_name, arguments)

        assert result is not None
        result_str = str(result).lower()

        if test_case["should_succeed"]:
            # Check for expected content if keywords provided
            if "expected_content_keywords" in test_case:
                for keyword in test_case["expected_content_keywords"]:
                    assert (
                        keyword.lower() in result_str
                    ), f"Expected keyword '{keyword}' not found in result: {result}"
        else:
            # Check for error indicators
            error_indicators = ["error", "failed", "exception", "traceback"]
            for indicator in error_indicators:
                assert (
                    indicator in result_str
                ), f"Expected error indicator '{indicator}' not found in result: {result}"

    @pytest.mark.asyncio
    async def test_tool_execution_timeout(self):
        """Test that tool execution handles timeouts properly."""
        tool_manager = self._create_tool_manager()

        timeout_seconds = 120

        server_name = "searching-mcp-server"
        tool_name = "google_search"
        arguments = {
            "q": "What is the capital of France?",
            "gl": "us",
            "hl": "en",
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
            "searching-mcp-server", "nonexistent_tool", {}
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
            "nonexistent_server", "google_search", {"q": "test", "gl": "us", "hl": "en"}
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
            {},  # Missing required arguments for google_search
            {"gl": "us", "hl": "en"},  # Empty query for google_search
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_arguments_google_search(self, invalid_args: Dict[str, Any]):
        """Test error handling for invalid arguments in google_search."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "searching-mcp-server", "google_search", invalid_args
        )

        assert result is not None
        result_str = str(result).lower()
        # Should contain error information about invalid arguments
        error_indicators = ["error", "invalid", "missing", "required", "empty"]
        assert any(
            indicator in result_str for indicator in error_indicators
        ), f"Expected error indicators not found for invalid arguments {invalid_args} in result: {result}"

    @pytest.mark.parametrize(
        "invalid_args",
        [
            {},  # Missing required entity argument
            {"entity": ""},  # Empty entity
        ],
    )
    @pytest.mark.asyncio
    async def test_invalid_arguments_wiki_search(self, invalid_args: Dict[str, Any]):
        """Test error handling for invalid arguments in wiki_search."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "searching-mcp-server", "wiki_search", invalid_args
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
                "tool_name": "google_search",
                "arguments": {
                    "q": "What is the capital of France?",
                    "gl": "us",
                    "hl": "en",
                },
            },
            {
                "tool_name": "wiki_search",
                "arguments": {"entity": "Paris", "summary_sentences": 3},
            },
            {
                "tool_name": "search_archived_webpage",
                "arguments": {"url": "https://www.google.com/"},
            },
        ]

        results = []
        for test_case in test_cases:
            result = await tool_manager.execute_tool_call(
                "searching-mcp-server", test_case["tool_name"], test_case["arguments"]
            )
            results.append(result)
            assert result is not None

        # Ensure we got different results for different tools
        assert len(results) == len(test_cases)
        assert all(result is not None for result in results)

    @pytest.mark.asyncio
    async def test_serper_api_key_not_set(self):
        """Test behavior when SERPER_API_KEY is not set for tools that require it."""
        # Create tool manager without SERPER_API_KEY
        tool_configs = [
            {
                "name": "searching-mcp-server",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=[
                        "-m",
                        "mirage.contrib.tools.mcp_servers.searching_mcp_server",
                    ],
                    env={},  # No API_KEY
                ),
            }
        ]
        tool_manager = ToolManager(tool_configs)

        # Test google_search without API key
        result = await tool_manager.execute_tool_call(
            "searching-mcp-server",
            "google_search",
            {"q": "test", "gl": "us", "hl": "en"},
        )

        assert result is not None
        result_str = str(result).lower()
        assert "api_key is not set" in result_str

        # Test scrape_website without API key
        result = await tool_manager.execute_tool_call(
            "searching-mcp-server",
            "scrape_website",
            {"url": "https://www.example.com/"},
        )

        assert result is not None
        result_str = str(result).lower()
        assert "api_key is not set" in result_str

        # Test that wiki_search still works without API_KEY
        result = await tool_manager.execute_tool_call(
            "searching-mcp-server", "wiki_search", {"entity": "Paris"}
        )

        assert result is not None
        result_str = str(result).lower()
        # Should not contain error since wiki_search doesn't need it
        assert "api_key is not set" not in result_str


# Configuration for pytest
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
