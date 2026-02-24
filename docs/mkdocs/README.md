# MiroFlow Documentation

This directory contains the MkDocs documentation site using the Material theme.

## Setup

Install required dependencies:

```bash
uv pip install mkdocs "mkdocs-material[imaging]"
```

## Local Development

Build and serve the documentation locally:

```bash
cd docs/mkdocs
uv run mkdocs build
uv run mkdocs serve -a localhost:9999
```

View at: http://localhost:9999

## Deployment

Deploy to GitHub Pages:

```bash
cd docs/mkdocs
uv run mkdocs gh-deploy --force
```

Live site: https://miromindai.github.io/miroflow/

## Documentation Structure

```
docs/
├── index.md                    # Landing page with changelog
├── license.md                  # Apache 2.0 license info
├── quickstart.md               # 5-minute quick start guide
├── core_concepts.md            # Architecture overview
├── yaml_config.md              # Configuration reference
├── evaluation_overview.md      # Benchmark performance summary
├── contribute_benchmarks.md    # How to add new benchmarks
├── contribute_tools.md         # How to add new MCP tools
├── contribute_llm_clients.md   # How to add new LLM clients
├── tool_*.md                   # Individual tool documentation
├── gaia_*.md                   # GAIA benchmark guides
├── browsecomp_*.md             # BrowseComp benchmark guides
├── hle*.md                     # HLE benchmark guides
├── webwalkerqa.md              # WebWalkerQA benchmark guide
├── futurex.md                  # FutureX benchmark guide
├── xbench_ds.md                # xBench-DS benchmark guide
├── finsearchcomp.md            # FinSearchComp benchmark guide
├── all_about_agents.md         # Curated agent research papers
├── data.md                     # MiroVerse dataset info
├── faqs.md                     # FAQ
└── assets/                     # Images and static files
```
