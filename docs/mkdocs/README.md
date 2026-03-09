# MiroFlow Documentation

This directory contains the MkDocs documentation site using the Material theme.

## Setup

mkdocs is included in the project's core dependencies. Just run:

```bash
uv sync
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
├── index.md                    # Landing page
├── why_miroflow.md             # Why MiroFlow — full narrative
├── whats_new.md                # What's New in v1.7
├── model_comparison.md         # Cross-model leaderboard
├── evaluation_overview.md      # Evaluation methodology
├── quickstart.md               # 5-minute quick start guide
├── core_concepts.md            # Architecture overview
├── yaml_config.md              # Configuration reference
├── contribute_benchmarks.md    # How to add new benchmarks
├── contribute_tools.md         # How to add new MCP tools
├── contribute_llm_clients.md   # How to add new LLM clients
├── llm_clients_overview.md     # LLM clients overview
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
