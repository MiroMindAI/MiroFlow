#!/bin/bash
# Deploy documentation to GitHub Pages
# Usage: ./scripts/update_docs.sh

cd docs/mkdocs

uv run mkdocs gh-deploy --force
