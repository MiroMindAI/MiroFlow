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

Live site: https://miromindai.github.io/MiroFlow/

Private repo site: https://MiroMindAI.github.io/miroflow-private-2026/

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
├── applications.md             # Demo and applications
├── faqs.md                     # FAQ
└── assets/                     # Images and static files
```

## Versioning (Optional, currently not in use)

This function is not in use as we found that some theme functions are not available under `mike`.

For versioned documentation using Mike:

```bash
# Install Mike
uv pip install mike

# Set default version
uv run mike set-default v0.3

# Deploy with version
uv run mike deploy --push --update-aliases v0.3 latest

# Serve versioned docs locally
uv run mike serve -a localhost:9999
```
