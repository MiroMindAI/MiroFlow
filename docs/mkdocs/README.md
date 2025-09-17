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



