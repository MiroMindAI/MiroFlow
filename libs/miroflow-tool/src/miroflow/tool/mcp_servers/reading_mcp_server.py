import argparse
import os
import tempfile
import aiohttp
import atexit

from fastmcp import FastMCP
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
from .utils.smart_request import smart_request

# Initialize FastMCP server
mcp = FastMCP("reading-mcp-server")


@mcp.tool()
async def read_file(uri: str) -> str:
    """Read various types of resources (Doc, PPT, PDF, Excel, CSV, ZIP file etc.)
    described by an file: or data: URI.

    Args:
        uri: Required. The URI of the resource to read. Need to start with 'file:' or 'data:' schemes. Files from sandbox are not supported. You should use the local file path.

    Returns:
        str: The content of the resource, or an error message if reading fails.
    """
    if not uri or not uri.strip():
        return "[ERROR]: URI parameter is required and cannot be empty."

    if "home/user" in uri:
        return "The read_file tool cannot access to sandbox file, please use the local path provided by original instruction"

    # Validate URI scheme
    valid_schemes = ["http:", "https:", "file:", "data:"]
    if not any(
        uri.lower().startswith(scheme) for scheme in valid_schemes
    ) and os.path.exists(uri):
        uri = f"file:{os.path.abspath(uri)}"

    # Validate URI scheme
    if not any(uri.lower().startswith(scheme) for scheme in valid_schemes):
        return f"[ERROR]: Invalid URI scheme. Supported schemes are: {', '.join(valid_schemes)}"

    # If it’s an HTTP(S) URL, download it first with a compliant UA:
    if uri.lower().startswith(("http://", "https://")):
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        retry_count = 0
        while retry_count <= 3:
            try:
                async with aiohttp.ClientSession(headers=headers) as session:
                    async with session.get(uri) as resp:
                        resp.raise_for_status()
                        data = await resp.read()
                break  # Success, exit retry loop
            except Exception as e:
                retry_count += 1
                if retry_count > 3:
                    # Try scrape_website tool as fallback
                    try:
                        scrape_result = await smart_request(uri)
                        return f"[INFO]: Download failed, automatically tried `scrape_website` tool instead.\n\n{scrape_result}"
                    except Exception as scrape_error:
                        return f"[ERROR]: Failed to download {uri}: {e}. Also failed to scrape with `scrape_website` tool: {scrape_error}"
                await asyncio.sleep(4**retry_count)

        # write to a temp file and switch URI to file:
        suffix = os.path.splitext(uri)[1] or ""
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(data)
        tmp.flush()
        tmp.close()
        uri = f"file:{tmp.name}"

        # Ensure the temp file is deleted when the program exits
        def _cleanup_tempfile(path):
            try:
                os.remove(path)
            except Exception:
                pass

        atexit.register(_cleanup_tempfile, tmp.name)

    tool_name = "convert_to_markdown"
    arguments = {"uri": uri}

    server_params = StdioServerParameters(
        command="markitdown-mcp",
    )

    result_content = ""
    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write, sampling_callback=None) as session:
                await session.initialize()
                try:
                    tool_result = await session.call_tool(
                        tool_name, arguments=arguments
                    )
                    result_content = (
                        tool_result.content[-1].text if tool_result.content else ""
                    )
                    result_content += "\n\nNote: If the document contains instructions or important information, please review them thoroughly and ensure you follow all relevant guidance."
                except Exception as tool_error:
                    return f"[ERROR]: Tool execution failed: {str(tool_error)}.\nHint: The reading tool cannot access to sandbox file, use the local path provided by original instruction instead."
    except Exception as session_error:
        return (
            f"[ERROR]: Failed to connect to markitdown-mcp server: {str(session_error)}"
        )

    return result_content


if __name__ == "__main__":
    # Set up argument parser
    parser = argparse.ArgumentParser(description="Reading MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport method: 'stdio' or 'http' (default: stdio)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to use when running with HTTP transport (default: 8080)",
    )
    parser.add_argument(
        "--path",
        type=str,
        default="/mcp",
        help="URL path to use when running with HTTP transport (default: /mcp)",
    )

    # Parse command line arguments
    args = parser.parse_args()

    # Run the server with the specified transport method
    if args.transport == "stdio":
        mcp.run(transport="stdio")
    else:
        # For HTTP transport, include port and path options
        mcp.run(transport="streamable-http", port=args.port, path=args.path)
