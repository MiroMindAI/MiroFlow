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

# Comment out any unwanted datasets by adding # at the start of the line
uv run -m src.utils.old.prepare_benchmark.main get gaia-val
uv run -m src.utils.old.prepare_benchmark.main get gaia-val-text-only
uv run -m src.utils.old.prepare_benchmark.main get frames-test
uv run -m src.utils.old.prepare_benchmark.main get webwalkerqa
uv run -m src.utils.old.prepare_benchmark.main get browsecomp-test
uv run -m src.utils.old.prepare_benchmark.main get browsecomp-zh-test
uv run -m src.utils.old.prepare_benchmark.main get hle
uv run -m src.utils.old.prepare_benchmark.main get hle-text-only
uv run -m src.utils.old.prepare_benchmark.main get xbench-ds
uv run -m src.utils.old.prepare_benchmark.main get futurex
uv run -m src.utils.old.prepare_benchmark.main get finsearchcomp
