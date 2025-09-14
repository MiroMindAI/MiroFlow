#!/bin/bash
echo "Please grant access to these datasets:"
echo "- https://huggingface.co/datasets/gaia-benchmark/GAIA"
echo "- https://huggingface.co/datasets/cais/hle"
echo

read -p "Have you granted access? [Y/n]: " answer
answer=${answer:-Y}
if [[ ! $answer =~ ^[Yy] ]]; then
    echo "Please grant access to the datasets first"
    exit 1
fi
echo "Access confirmed"


uv run main.py prepare-benchmark get gaia-val
uv run main.py prepare-benchmark get gaia-val-text-only
uv run main.py prepare-benchmark get frames-test
uv run main.py prepare-benchmark get webwalkerqa
uv run main.py prepare-benchmark get browsecomp-test
uv run main.py prepare-benchmark get browsecomp-zh-test
uv run main.py prepare-benchmark get hle