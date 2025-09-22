# Searching Tools (`searching_mcp_server.py`)

The Searching MCP Server provides comprehensive search capabilities including Google search, Wikipedia content retrieval, archive searching, and web scraping functionality.

!!! info "Available Functions"
    This MCP server provides the following functions that agents can call:
    
    - **Google Search**: Comprehensive web search with filtering and localization
    - **Wikipedia Access**: Page content retrieval and revision history tracking
    - **Archive Search**: Wayback Machine integration for historical web content
    - **Web Scraping**: Content extraction from websites and YouTube videos

---

## Environment Variables

The following environment variables configure the search tools:

- `SERPER_API_KEY`: Required API key for Serper service, used by `google_search` and as a fallback for `scrape_website`
- `JINA_API_KEY`: Required API key for JINA service. Default choice for scraping websites in `scrape_website`
- `REMOVE_SNIPPETS`: Set to "true" to filter out snippets from results. Used in `google_search` to filter the search results returned by Serper
- `REMOVE_KNOWLEDGE_GRAPH`: Set to "true" to remove knowledge graph data. Used in `google_search` to filter the search results returned by Serper
- `REMOVE_ANSWER_BOX`: Set to "true" to remove answer box content. Used in `google_search` to filter the search results returned by Serper

---

## Function Reference

The following functions are provided by the `searching_mcp_server.py` MCP tool and can be called by agents:

### `google_search(q: str, gl: str = "us", hl: str = "en", location: str = None, num: int = 10, tbs: str = None, page: int = 1)`

Perform Google searches via Serper API and retrieve rich search results including organic results, people also ask, related searches, and knowledge graph.

**Parameters:**

- `q`: Search query string
- `gl`: Country context for search (e.g., 'us' for United States, 'cn' for China, 'uk' for United Kingdom). Default: 'us'
- `hl`: Google interface language (e.g., 'en' for English, 'zh' for Chinese, 'es' for Spanish). Default: 'en'
- `location`: City-level location for search results (e.g., 'SoHo, New York, United States', 'California, United States')
- `num`: Number of results to return. Default: 10
- `tbs`: Time-based search filter ('qdr:h' for past hour, 'qdr:d' for past day, 'qdr:w' for past week, 'qdr:m' for past month, 'qdr:y' for past year)
- `page`: Page number of results to return. Default: 1

**Returns:**

- `str`: JSON formatted search results with organic results and related information

**Features:**

- Automatic retry mechanism (up to 5 attempts)
- Configurable result filtering via environment variables
- Support for regional and language-specific searches

---

### `wiki_get_page_content(entity: str, first_sentences: int = 10)`

Get specific Wikipedia page content for entities (people, places, concepts, events) and return structured information.

**Parameters:**

- `entity`: The entity to search for in Wikipedia
- `first_sentences`: Number of first sentences to return from the page. Set to 0 to return full content. Default: 10

**Returns:**

- `str`: Formatted content containing page title, introduction/full content, and URL

**Features:**

- Handles disambiguation pages automatically
- Provides clean, structured output
- Fallback search suggestions when page not found
- Automatic content truncation for manageable output

---

### `search_wiki_revision(entity: str, year: int, month: int, max_revisions: int = 50)`

Search for an entity in Wikipedia and return the revision history for a specific month.

**Parameters:**

- `entity`: The entity to search for in Wikipedia
- `year`: The year of the revision (e.g., 2024)
- `month`: The month of the revision (1-12)
- `max_revisions`: Maximum number of revisions to return. Default: 50

**Returns:**

- `str`: Formatted revision history with timestamps, revision IDs, and URLs

**Features:**

- Automatic date validation and adjustment
- Support for date range from 2000 to current year
- Detailed revision metadata including timestamps and direct links
- Clear error handling for invalid dates or missing pages

---

### `search_archived_webpage(url: str, year: int, month: int, day: int)`

Search the Wayback Machine (archive.org) for archived versions of a webpage for a specific date.

**Parameters:**

- `url`: The URL to search for in the Wayback Machine
- `year`: The target year (e.g., 2023)
- `month`: The target month (1-12)
- `day`: The target day (1-31)

**Returns:**

- `str`: Formatted archive information including archived URL, timestamp, and availability status

**Features:**

- Automatic URL protocol detection and correction
- Date validation and adjustment (1995 to present)
- Fallback to most recent archive if specific date not found
- Special handling for Wikipedia URLs with tool suggestions
- Automatic retry mechanism for reliable results

---

### `scrape_website(url: str)`

Scrape website content including support for regular websites and YouTube video information.

**Parameters:**

- `url`: The URL of the website to scrape

**Returns:**

- `str`: Scraped website content including text, metadata, and structured information

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI