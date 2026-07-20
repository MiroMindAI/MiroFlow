# Xquik X Search (`tool-xquik`)

`tool-xquik` adds source-specific X post search to MiroFlow through an opt-in
FastMCP server. It returns the Xquik cursor response unchanged so agents can
inspect post text, author data, engagement counts, and pagination state.

## Configuration

Set the API key before starting MiroFlow:

```bash
export XQUIK_API_KEY="your-api-key"
```

Optional settings:

```bash
export XQUIK_BASE_URL="https://xquik.com"
export XQUIK_REQUEST_TIMEOUT="30"
```

Add the tool to an agent configuration without changing the default tool set:

```yaml
main_agent:
  tool_config:
    - tool-reasoning
    - tool-xquik
```

## Tool

### `search_x_tweets`

| Parameter | Type | Default | Description |
| --- | --- | --- | --- |
| `query` | string | required | X search query or operators |
| `limit` | integer | `20` | Results to return, from 1 through 200 |
| `query_type` | string | `Latest` | `Latest` or `Top` ordering |
| `cursor` | string | optional | Cursor returned by a previous search |

The result is JSON with `tweets`, `has_next_page`, and `next_cursor` fields.
Pass the next cursor to a follow-up tool call when additional pages are needed.

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.
