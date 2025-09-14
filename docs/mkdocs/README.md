# MiroFlow Documentation Commands

## Setup (one-time)
```bash
uv pip install mkdocs 
uv pip install "mkdocs-material[imaging]"
uv pip install mike
```

## How to add docs:
https://squidfunk.github.io/mkdocs-material/setup/setting-up-versioning/?h=version

```bash

# must run
uv run mike set-default v0.3

# to view locally
uv run mike serve -a localhost:9999

# to push to remote
uv run mike deploy --push --update-aliases v0.3 latest

# Other commands - may not be useful
# uv run mike delete --all
uv run mike set-default --push latest
uv run mike build
uv run mike deploy v0.3
```



# Material Theme (no longer needed)

## Local Development
```bash
cd docs/mkdocs
uv run mkdocs build
uv run mkdocs serve -a localhost:9999
```
View at: http://localhost:8000

## Deploy to GitHub Pages
```bash
cd docs/mkdocs/miroflow-project
uv run mkdocs gh-deploy --force
```
Live site: https://miromindai.github.io/MiroFlow/

