# MiroAPI

!!! warning "Preview Documentation"
    This service is currently in preview and limited to internal access. Public release will follow once it is production-ready.

## Overview
MiroAPI provides an internal caching layer for Serper Search and Jina Scrape to reduce costs, speed up development, and enable reproducible "go-back-in-time" sandbox runs by serving recorded results when available.

### Step 1: Apply for a MiroAPI key
    Request a MiroAPI key through the internal portal.

### Step 2: Configure .env
```
# API for Google Search (recommended)
SERPER_API_KEY="svc-miro-api01-replace-with-your-key"
SERPER_BASE_URL="https://miro-api.miromind.site/serper"

# API for Web Scraping (recommended)
JINA_API_KEY="svc-miro-api01-replace-with-your-key"
JINA_BASE_URL="https://miro-api.miromind.site/jina"
```


    