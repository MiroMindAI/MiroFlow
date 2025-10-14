# Searching Tools - Serper (`tool-searching-serper`)

Lightweight Google search and web scraping via Serper API using NPM package.

!!! tip "Which Tool to Use?"
    - **`tool-searching-serper`**: Fast Google search + basic scraping (NPM-based)
    - **`tool-searching`**: Full-featured with Wikipedia, Archive.org, JINA (Python-based)

---

## Configuration

```yaml title="Agent Configuration"
main_agent:
  tool_config: 
    - tool-searching-serper
```

**Environment Variables:**

- `SERPER_API_KEY`: **Required**. Get at [serper.dev](https://serper.dev)

---

## Function Reference

### `google_search(q: str, gl: str = "us", hl: str = "en", location: str = None, num: int = 10, tbs: str = None, page: int = 1)`

Perform Google searches via Serper API.

**Parameters:**

- `q`: Search query (required)
- `gl`: Country code (e.g., 'us', 'uk', 'cn'). Default: 'us'
- `hl`: Language (e.g., 'en', 'zh', 'es'). Default: 'en'
- `location`: City location (e.g., 'San Francisco, California, United States')
- `num`: Number of results. Default: 10
- `tbs`: Time filter ('qdr:h'=hour, 'qdr:d'=day, 'qdr:w'=week, 'qdr:m'=month, 'qdr:y'=year)
- `page`: Page number. Default: 1

**Returns:**

- `str`: JSON formatted search results

**Example:**

```python
# Basic search
results = await google_search("artificial intelligence")

# With filters
results = await google_search("latest news", tbs="qdr:d", num=20)
```

---

### `scrape(url: str)`

Scrape website content using Serper.

**Parameters:**

- `url`: Website URL to scrape

**Returns:**

- `str`: Scraped content

**Example:**

```python
content = await scrape("https://example.com/article")
```

---

## Comparison: Serper vs Full Searching

| Feature | `tool-searching-serper` | `tool-searching` |
|---------|------------------------|------------------|
| Google Search | ✅ | ✅ |
| Web Scraping | ✅ Basic | ✅ Advanced |
| Wikipedia | ❌ | ✅ |
| Archive.org | ❌ | ✅ |
| YouTube Info | ❌ | ✅ |
| Speed | ⚡ Faster | Slightly slower |
| Dependencies | Node.js/NPM | Python only |

---

!!! info "Documentation Info"
    **Last Updated:** October 2025 · **Doc Contributor:** Team @ MiroMind AI
