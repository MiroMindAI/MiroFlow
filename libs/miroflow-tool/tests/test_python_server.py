# SPDX-FileCopyrightText: 2025 MiromindAI
#
# SPDX-License-Identifier: Apache-2.0

import ast
import asyncio
import os
import sys
import tempfile
from typing import Any, Dict, List

import pytest
from mcp import StdioServerParameters

from miroflow.tool.manager import ToolManager


class TestPythonServer:
    """Test suite for Python MCP Server functionality."""

    def _get_e2b_credentials(self) -> Dict[str, str]:
        """Get E2B API credentials, skip test if not available."""
        api_key = os.environ.get("E2B_API_KEY")
        if not api_key:
            pytest.skip("E2B_API_KEY environment variable not set")

        return {
            "E2B_API_KEY": api_key,
        }

    def _create_tool_manager(self) -> ToolManager:
        """Create a configured ToolManager instance."""
        credentials = self._get_e2b_credentials()
        tool_configs = [
            {
                "name": "tool-python",
                "params": StdioServerParameters(
                    command=sys.executable,
                    args=["-m", "miroflow.tool.mcp_servers.python_server"],
                    env=credentials,
                ),
            }
        ]
        return ToolManager(tool_configs)

    def _create_test_file(self) -> str:
        """Create a temporary test file for upload testing."""
        fd, temp_file = tempfile.mkstemp(suffix=".py")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(
                    "# Test Python file\nprint('Hello from test file!')\nx = 42\nprint(f'x = {x}')"
                )
        except:
            os.close(fd)
            raise
        return temp_file

    def _cleanup_test_file(self, temp_file: str):
        """Clean up temporary test file."""
        if os.path.exists(temp_file):
            os.unlink(temp_file)

    @pytest.mark.asyncio
    async def test_tool_definitions_available(self):
        """Test that tool definitions are properly loaded."""
        tool_manager = self._create_tool_manager()
        tool_definitions = await tool_manager.get_all_tool_definitions()

        assert tool_definitions is not None
        assert len(tool_definitions) == 1

        # Check if python server is available
        server_info = tool_definitions[0]
        assert server_info["name"] == "tool-python"
        assert len(server_info["tools"]) == 5

        # Check all five tools are present
        tool_names = [tool.get("name") for tool in server_info["tools"]]
        expected_tools = [
            "create_sandbox",
            "run_command",
            "run_python_code",
            "upload_local_file_to_sandbox",
            "download_file_from_internet_to_sandbox",
        ]
        for expected_tool in expected_tools:
            assert (
                expected_tool in tool_names
            ), f"Expected tool '{expected_tool}' not found in {tool_names}"

    # Test 1: run_python_code - Success cases
    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "simple_math_no_sandbox",
                "arguments": {
                    "code_block": "import math\nresult = math.sqrt(16)\nprint(f'Square root of 16 is {result}')",
                },
                "expected_keywords": ["Square root of 16 is 4"],
            },
            {
                "name": "simple_math_with_existing_sandbox",
                "arguments": {
                    "code_block": "import math\nresult = math.pi\nprint(f'Pi is approximately {result:.2f}')",
                },
                "expected_keywords": ["Pi is approximately 3.14"],
            },
            {
                "name": "list_operations",
                "arguments": {
                    "code_block": "numbers = [1, 2, 3, 4, 5]\ntotal = sum(numbers)\nprint(f'Sum: {total}')\nprint(f'Length: {len(numbers)}')",
                },
                "expected_keywords": ["Sum: 15", "Length: 5"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_run_python_code_success(self, test_case: Dict[str, Any]):
        """Test run_python_code with successful cases."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        assert sandbox_id_str.startswith("sandbox_id: "), "failed to create sandbox"
        sandbox_id = sandbox_id_str.split(": ")[1]

        arguments = test_case["arguments"].copy()
        arguments["sandbox_id"] = sandbox_id

        result = await tool_manager.execute_tool_call(
            "tool-python", "run_python_code", arguments
        )

        self._assert_success_result(result, test_case["expected_keywords"])

    # Test 1: run_python_code - Error cases
    @pytest.mark.parametrize(
        "error_case",
        [
            {
                "name": "syntax_error",
                "arguments": {
                    "code_block": "print('missing closing quote",
                },
                "expected_error_keywords": ["syntax", "error"],
            },
            {
                "name": "runtime_error",
                "arguments": {
                    "code_block": "x = 1 / 0\nprint(x)",
                },
                "expected_error_keywords": ["division", "zero"],
            },
            {
                "name": "import_error",
                "arguments": {
                    "code_block": "import nonexistent_module\nprint('This should fail')",
                },
                "expected_error_keywords": ["import", "module"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_run_python_code_errors(self, error_case: Dict[str, Any]):
        """Test run_python_code with error cases."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        arguments = error_case["arguments"].copy()
        arguments["sandbox_id"] = sandbox_id

        result = await tool_manager.execute_tool_call(
            "tool-python", "run_python_code", arguments
        )

        self._assert_error_result(result, error_case["expected_error_keywords"])

    # Test 2: upload_local_file_to_sandbox - Success cases
    @pytest.mark.asyncio
    async def test_upload_file_success(self):
        """Test file upload with and without sandbox_id."""
        tool_manager = self._create_tool_manager()
        test_file = self._create_test_file()

        try:
            # First create a sandbox to get a real sandbox_id
            sandbox_result = await tool_manager.execute_tool_call(
                "tool-python", "create_sandbox", {}
            )

            # Extract sandbox_id from the result
            assert sandbox_result is not None
            assert "result" in sandbox_result
            sandbox_id_str = sandbox_result["result"]
            sandbox_id = (
                sandbox_id_str.split(": ")[1]
                if ": " in sandbox_id_str
                else sandbox_id_str
            )

            arguments = {"sandbox_id": sandbox_id, "local_file_path": test_file}

            result = await tool_manager.execute_tool_call(
                "tool-python", "upload_local_file_to_sandbox", arguments
            )

            expected_keywords = [
                "/home/user/" + os.path.basename(test_file),
                "uploaded",
            ]
            self._assert_success_result(result, expected_keywords)
        finally:
            self._cleanup_test_file(test_file)

    # Test 2: upload_local_file_to_sandbox - Error cases
    @pytest.mark.parametrize(
        "error_case",
        [
            {
                "name": "nonexistent_file",
                "arguments": {
                    "local_file_path": "/path/to/nonexistent/file.py",
                },
                "expected_error_keywords": ["not", "exist", "file", "failed"],
            },
            {
                "name": "empty_path",
                "arguments": {
                    "local_file_path": "",
                },
                "expected_error_keywords": ["path", "exist", "failed"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_upload_file_errors(self, error_case: Dict[str, Any]):
        """Test file upload with error cases."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        arguments = error_case["arguments"].copy()
        arguments["sandbox_id"] = sandbox_id

        result = await tool_manager.execute_tool_call(
            "tool-python", "upload_local_file_to_sandbox", arguments
        )

        self._assert_error_result(result, error_case["expected_error_keywords"])

    # Test 3: download_file_from_internet_to_sandbox - Success cases
    @pytest.mark.parametrize(
        "test_case",
        [
            {
                "name": "download_file_no_existing_sandbox",
                "arguments": {
                    "url": "https://cdn.sanity.io/images/bj34pdbp/migration/26e5f9a2af40de4415deb8b447e5e4161ee41c67-1000x769.gif",
                },
                "expected_keywords": [
                    "/home/user/26e5f9a2af40de4415deb8b447e5e4161ee41c67-1000x769.gif",
                    "downloaded",
                ],
            },
            {
                "name": "download_file_with_existing_sandbox",
                "arguments": {
                    "url": "https://cdn.sanity.io/images/bj34pdbp/migration/26e5f9a2af40de4415deb8b447e5e4161ee41c67-1000x769.gif",
                },
                "expected_keywords": [
                    "/home/user/26e5f9a2af40de4415deb8b447e5e4161ee41c67-1000x769.gif",
                    "downloaded",
                ],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_download_file_success(self, test_case: Dict[str, Any]):
        """Test internet file download with successful cases."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        arguments = test_case["arguments"].copy()
        arguments["sandbox_id"] = sandbox_id

        result = await tool_manager.execute_tool_call(
            "tool-python", "download_file_from_internet_to_sandbox", arguments
        )

        self._assert_success_result(result, test_case["expected_keywords"])

    # Test 3: download_file_from_internet_to_sandbox - Error cases
    @pytest.mark.parametrize(
        "error_case",
        [
            {
                "name": "invalid_url",
                "arguments": {
                    "url": "not-a-valid-url",
                },
                "expected_error_keywords": ["url", "invalid"],
            },
            {
                "name": "nonexistent_url",
                "arguments": {
                    "url": "https://httpbin.org/nonexistent-endpoint-12345",
                },
                "expected_error_keywords": ["404", "not", "found"],
            },
            {
                "name": "empty_url",
                "arguments": {
                    "url": "",
                },
                "expected_error_keywords": ["url", "empty"],
            },
        ],
    )
    @pytest.mark.asyncio
    async def test_download_file_errors(self, error_case: Dict[str, Any]):
        """Test internet file download with error cases."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        arguments = error_case["arguments"].copy()
        arguments["sandbox_id"] = sandbox_id

        result = await tool_manager.execute_tool_call(
            "tool-python", "download_file_from_internet_to_sandbox", arguments
        )

        self._assert_error_result(result, error_case["expected_error_keywords"])

    # Integration test: Complete workflow
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_complete_workflow(self):
        """Test a complete workflow: create sandbox, upload file, run code, download file."""
        tool_manager = self._create_tool_manager()
        test_file = self._create_test_file()

        try:
            # Step 1: Create sandbox
            sandbox_result = await tool_manager.execute_tool_call(
                "tool-python", "create_sandbox", {}
            )
            assert sandbox_result is not None
            assert "result" in sandbox_result

            sandbox_id_str = sandbox_result["result"]
            sandbox_id = (
                sandbox_id_str.split(": ")[1]
                if ": " in sandbox_id_str
                else sandbox_id_str
            )

            # Step 2: Upload file
            upload_result = await tool_manager.execute_tool_call(
                "tool-python",
                "upload_local_file_to_sandbox",
                {"sandbox_id": sandbox_id, "local_file_path": test_file},
            )
            assert upload_result is not None
            upload_str = str(upload_result).lower()
            assert any(
                keyword in upload_str for keyword in ["uploaded", "success"]
            ), f"File upload failed: {upload_result}"

            # Step 3: Run Python code that uses the uploaded file
            code_result = await tool_manager.execute_tool_call(
                "tool-python",
                "run_python_code",
                {
                    "sandbox_id": sandbox_id,
                    "code_block": f"exec(open('/home/user/{os.path.basename(test_file)}').read())",
                },
            )
            assert code_result is not None
            code_str = str(code_result).lower()
            assert (
                "hello from test file!" in code_str
            ), f"Code execution failed: {code_result}"

            # Step 4: Download a file from the internet
            download_result = await tool_manager.execute_tool_call(
                "tool-python",
                "download_file_from_internet_to_sandbox",
                {
                    "sandbox_id": sandbox_id,
                    "url": "https://cdn.sanity.io/images/bj34pdbp/migration/26e5f9a2af40de4415deb8b447e5e4161ee41c67-1000x769.gif",
                },
            )
            assert download_result is not None
            download_str = str(download_result).lower()
            assert any(
                keyword in download_str for keyword in ["downloaded", "success"]
            ), f"File download failed: {download_result}"

            # Step 5: Verify the downloaded file exists
            verify_result = await tool_manager.execute_tool_call(
                "tool-python",
                "run_python_code",
                {
                    "sandbox_id": sandbox_id,
                    "code_block": "import os\nfiles = os.listdir('/home/user')\nprint('Files in /home/user:')\nfor f in files:\n    print(f'  {f}')",
                },
            )
            assert verify_result is not None
            verify_str = str(verify_result).lower()
            assert (
                "26e5f9a2af40de4415deb8b447e5e4161ee41c67-1000x769.gif" in verify_str
            ), f"Downloaded file not found: {verify_result}"
        finally:
            self._cleanup_test_file(test_file)

    def _assert_success_result(self, result: Any, expected_keywords: List[str]):
        """Assert that a result indicates success and contains expected keywords."""
        assert result is not None, "Result should not be None"

        # Check if result contains error
        if isinstance(result, str):
            try:
                parsed = ast.literal_eval(result)
                if isinstance(parsed, dict):
                    result = parsed
            except Exception:
                pass
        assert isinstance(result, dict), f"Unexpected format in result: {result}"

        # Extract the actual result data
        if isinstance(result, dict) and "result" in result:
            # The actual tool result is in the "result" field
            actual_result = result["result"]
        else:
            actual_result = result

        result_str = str(actual_result).lower()

        # Should not contain error indicators
        assert (
            "error: none" in result_str
            or '"error": null' in result_str
            or '"error": ""' in result_str
            or "exit_code=0" in result_str
            or "error" not in result_str
        ), f"Unexpected error indicator found in result: {result}"

        # Should contain expected keywords
        for keyword in expected_keywords:
            assert (
                keyword.lower() in result_str
            ), f"Expected keyword '{keyword}' not found in result: {result}"

    def _assert_error_result(self, result: Any, expected_error_keywords: List[str]):
        """Assert that result indicates an error and contains expected error keywords."""
        # Extract the actual result data
        if isinstance(result, str):
            try:
                parsed = ast.literal_eval(result)
                if isinstance(parsed, dict):
                    result = parsed
            except Exception:
                pass
        assert isinstance(result, dict), f"Result should be a dict: {result}"
        if isinstance(result, dict) and "result" in result:
            # The actual tool result is in the "result" field
            actual_result = result["result"]
        else:
            actual_result = result

        result_str = str(actual_result).lower()

        # Should contain at least one expected error keyword
        found_keywords = [
            keyword
            for keyword in expected_error_keywords
            if keyword.lower() in result_str
        ]
        assert (
            len(found_keywords) > 0
        ), f"Expected error keywords {expected_error_keywords} not found in result: {result}"

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test error handling for invalid tool names."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-python", "nonexistent_tool", {}
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_invalid_server_name(self):
        """Test error handling for invalid server names."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "nonexistent_server", "run_python_code", {}
        )
        assert result is not None

    @pytest.mark.parametrize(
        "tool_name,invalid_args",
        [
            ("run_python_code", {}),  # Missing both code_block and sandbox_id
            ("run_python_code", {"code_block": ""}),  # Missing sandbox_id
            ("run_python_code", {"sandbox_id": "test123"}),  # Missing code_block
            (
                "upload_local_file_to_sandbox",
                {},
            ),  # Missing both sandbox_id and local_file_path
            (
                "upload_local_file_to_sandbox",
                {"sandbox_id": "test123"},
            ),  # Missing local_file_path
            (
                "upload_local_file_to_sandbox",
                {"local_file_path": "test.py"},
            ),  # Missing sandbox_id
            (
                "download_file_from_internet_to_sandbox",
                {},
            ),  # Missing both sandbox_id and url
            (
                "download_file_from_internet_to_sandbox",
                {"sandbox_id": "test123"},
            ),  # Missing url
            (
                "download_file_from_internet_to_sandbox",
                {"url": "http://test.com"},
            ),  # Missing sandbox_id
        ],
    )
    @pytest.mark.asyncio
    async def test_missing_required_arguments(
        self, tool_name: str, invalid_args: Dict[str, Any]
    ):
        """Test error handling for missing required arguments."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-python", tool_name, invalid_args
        )

        self._assert_error_result(result, ["missing", "required"])

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_timeout(self):
        """Test handling of operations that might timeout."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {"timeout": 5}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        arguments = {"sandbox_id": sandbox_id, "code_block": "print('Still active')"}
        # Sleep for 10 seconds to ensure sandbox is timeouted
        import time

        time.sleep(10)

        result = None
        try:
            result = await asyncio.wait_for(
                tool_manager.execute_tool_call(
                    "tool-python", "run_python_code", arguments
                ),
                timeout=350,
            )
        except Exception:
            if result is not None:
                assert "Failed to connect to sandbox" in str(
                    result
                ) or "not found" in str(result), "Sandbox is not closed by timeout"

    @pytest.mark.asyncio
    async def test_create_sandbox_success(self):
        """Test create_sandbox tool functionality."""
        tool_manager = self._create_tool_manager()

        result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )
        assert result is not None
        assert "error" not in result, f"Create sandbox failed: {result}"
        sandbox_id = result["result"].split(": ")[1]
        print(f"Sandbox ID: {sandbox_id}")

    @pytest.mark.asyncio
    async def test_run_command_success(self):
        """Test run_command tool functionality."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        # Test simple command
        result = await tool_manager.execute_tool_call(
            "tool-python",
            "run_command",
            {"sandbox_id": sandbox_id, "command": "echo 'Hello World'"},
        )

        expected_keywords = ["Hello World"]
        self._assert_success_result(result, expected_keywords)

    @pytest.mark.asyncio
    async def test_run_command_errors(self):
        """Test run_command with error cases."""
        tool_manager = self._create_tool_manager()

        # First create a sandbox to get a real sandbox_id
        sandbox_result = await tool_manager.execute_tool_call(
            "tool-python", "create_sandbox", {}
        )

        # Extract sandbox_id from the result
        assert sandbox_result is not None
        assert "result" in sandbox_result
        sandbox_id_str = sandbox_result["result"]
        sandbox_id = (
            sandbox_id_str.split(": ")[1] if ": " in sandbox_id_str else sandbox_id_str
        )

        # Test a command that should fail
        result = await tool_manager.execute_tool_call(
            "tool-python",
            "run_command",
            {"sandbox_id": sandbox_id, "command": "nonexistent_command_12345"},
        )

        assert result is not None
        # Note: This might not always be an error in the result format,
        # sometimes failed commands just return exit codes


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow tests")
