# Python Tools (`python_server.py`)

The Python Execution Server provides a secure sandboxed environment for running Python code and shell commands using E2B server. This tool enables agents to execute code safely, manipulate files, and perform computational tasks in an isolated environment.

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Sandbox Management**: Create and manage isolated execution environments
    - **Code Execution**: Run Python code and shell commands safely
    - **File Operations**: Upload, download, and transfer files between local and sandbox
    - **Internet Access**: Download files directly from web sources to sandbox

---

## Function Reference

The following functions are provided by the `python_server.py` MCP tool and can be called by agents:

### `create_sandbox()`

Creates a Linux sandbox for safely executing commands and running Python code.

**Returns:**
- `str`: The `sandbox_id` of the newly created sandbox

!!! warning "Important Usage Notes"
    - **Required First Step**: This tool must be called before using other tools within this MCP server
    - **Session Management**: The sandbox may timeout and automatically shut down after inactivity
    - **Pre-installed Environment**: The sandbox comes pre-installed with common packages for data science and document processing. For a detailed list and advanced usage information, see [E2B Extension](./e2b_extension.md)

---

### `run_command(sandbox_id: str, command: str)`

Execute shell commands in the Linux sandbox.

**Parameters:**
- `sandbox_id`: ID of the existing sandbox (must be created first)
- `command`: Shell command to execute

**Returns:**
- `str`: Command execution result (stderr, stdout, exit_code, error)

**Features:**
- Automatic retry mechanism
- Permission hints for sudo commands

---

### `run_python_code(sandbox_id: str, code_block: str)`

Run Python code in the sandbox and return execution results.

**Parameters:**
- `sandbox_id`: ID of the existing sandbox
- `code_block`: Python code to execute

**Returns:**
- `str`: Code execution result (stderr, stdout, exit_code, error)

**Features:**
- Automatic retry mechanism

---

### `upload_file_from_local_to_sandbox(sandbox_id: str, local_file_path: str, sandbox_file_path: str = "/home/user")`

Upload local files to the sandbox environment.

!!! note "When to Use"
    When a local file is provided to the agent, the agent needs to call this tool to copy the file from local storage to the sandbox for further file processing.

**Parameters:**
- `sandbox_id`: ID of the existing sandbox
- `local_file_path`: Local path of the file to upload
- `sandbox_file_path`: Target directory in sandbox (default: `/home/user`)

**Returns:**
- `str`: Path of uploaded file in sandbox or error message

---

### `download_file_from_internet_to_sandbox(sandbox_id: str, url: str, sandbox_file_path: str = "/home/user")`

Download files from the internet directly to the sandbox.

**Parameters:**
- `sandbox_id`: ID of the existing sandbox
- `url`: URL of the file to download
- `sandbox_file_path`: Target directory in sandbox (default: `/home/user`)

**Returns:**
- `str`: Path of downloaded file in sandbox or error message

**Features:**
- Automatic retry mechanism

---

### `download_file_from_sandbox_to_local(sandbox_id: str, sandbox_file_path: str, local_filename: str = None)`

Download files from sandbox to local system for processing by other tools.

!!! tip "Inter-tool Communication"
    Other MCP tools (such as visual question answering) cannot access files in a sandbox. Therefore, this tool should be called when the agent wants other tools to analyze files in the sandbox.

**Parameters:**
- `sandbox_id`: ID of the sandbox
- `sandbox_file_path`: Path of file in sandbox
- `local_filename`: Optional local filename (uses original if not provided)

**Returns:**
- `str`: Local path of downloaded file or error message

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI