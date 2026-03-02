---
name: simple_file_understanding
description: Understand and analyze CSV files. Use when the task involves reading, parsing, or answering questions about data in a CSV file.
---

# simple_file_understanding

## Instructions

When a task involves a CSV file, follow this workflow:

### Step 1: Read the File
Use the `read_file` tool from the `tool-reading` MCP server to load the file content. Provide the full local file path as the `uri` argument.

### Step 2: Understand the Structure
After reading the file, identify:
- **Column headers**: The first row typically contains column names.
- **Data types**: Determine whether each column contains numbers, text, dates, or mixed types.
- **Row count**: Note the approximate number of data rows.
- **Delimiter**: CSV files use commas by default, but the content returned will already be converted to markdown table format.

### Step 3: Answer the Question
When answering questions about the CSV data:
- **Filtering**: To find rows matching a condition (e.g., "names starting with Co"), scan the relevant column and apply the filter.
- **Sorting**: If the question asks for "first", "last", "highest", or "lowest", identify the ordering criterion. Unless otherwise specified, "first" means the first matching row in the file's original order (top to bottom).
- **Aggregation**: For questions involving counts, sums, averages, or other aggregations, compute them from the relevant column values.
- **Exact matching**: Pay close attention to exact string matching vs. prefix/substring matching. "Starting with Co" means the value begins with "Co", not just contains "Co".

### Important Notes
- Always read the file before attempting to answer. Do not guess the content.
- If the file is large and the markdown output is truncated, focus on the portions relevant to the question.
- Provide the final answer clearly and concisely, wrapped in \boxed{}.
