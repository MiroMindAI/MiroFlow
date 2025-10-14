# Reading Tools (`tool-reading`)

Read and convert various document formats (DOC, PDF, Excel, etc.) to markdown for easy processing.

---

## Configuration

```yaml title="Agent Configuration"
main_agent:
  tool_config: 
    - tool-reading
```

**Environment Variables:**

- `SERPER_API_KEY`: Required for certain operations
- `JINA_API_KEY`: Required for document processing

---

## Function Reference

### `read_file(uri: str)`

Read various types of resources and convert them to markdown format.

**Parameters:**

- `uri`: The URI or path of the resource to read. Supported:
  - Local file paths (e.g., `/path/to/document.pdf`)
  - `file:` URIs (e.g., `file:/path/to/document.pdf`)
  - `http:` / `https:` URLs (will be downloaded automatically)
  - `data:` URIs (base64-encoded)

**Supported Formats:**

- Documents: DOC, DOCX, RTF, ODT
- Presentations: PPT, PPTX, ODP
- Spreadsheets: XLS, XLSX, CSV, ODS
- PDFs: PDF documents
- Archives: ZIP files
- Images and text files

**Returns:**

- `str`: Content in markdown format, or error message if reading fails

**Example:**

```python
# Read a local PDF
result = await read_file("file:/path/to/document.pdf")

# Read from URL
result = await read_file("https://example.com/report.pdf")

# Read local file (auto-converted to file: URI)
result = await read_file("/data/spreadsheet.xlsx")
```

**Important Notes:**

- Cannot access E2B sandbox files (`/home/user/`)
- Use local file paths provided in the original instruction
- Downloaded files are automatically cleaned up

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
