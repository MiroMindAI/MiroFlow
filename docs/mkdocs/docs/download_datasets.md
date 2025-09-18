# Dataset Download Instructions

This guide walks you through downloading and preparing benchmark datasets for MiroFlow evaluation.

## Prerequisites

!!! warning "Important"
    Before downloading datasets, ensure you have completed both access requests and environment setup below.

### 1. Request Dataset Access

You must request access to the following Hugging Face datasets:

!!! info "Required Datasets"
    - **GAIA Dataset**: [https://huggingface.co/datasets/gaia-benchmark/GAIA](https://huggingface.co/datasets/gaia-benchmark/GAIA)
    - **HLE Dataset**: [https://huggingface.co/datasets/cais/hle](https://huggingface.co/datasets/cais/hle)

Visit the links above and request access to both datasets.

### 2. Configure Environment Variables

Copy the template file and create your environment configuration:

```bash
cp .env.template .env
```

Edit the `.env` file and configure these essential variables:

```env title=".env"
# Required: Your Hugging Face token for dataset access
HF_TOKEN="your-actual-huggingface-token-here"

# Data directory path 
DATA_DIR="data/"
```

!!! tip "Getting Your Hugging Face Token"
    1. Go to [https://huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)
    2. Create a new token with at least "Read" permissions
    3. Replace `your-actual-huggingface-token-here` in the `.env` file with your actual token

## Download and Prepare Datasets

Once you have been granted access to the required datasets, run the preparation script to download all benchmark datasets.

### Running the Download Script

Execute the following command to start the download process for all datasets, if a single dataset is needed, you could run the specific command:

```bash
bash scripts/run_prepare_benchmark.sh
```

!!! note "Script Contents"
    The script contains the following logic and dataset downloads. You can comment out any unwanted datasets by adding `#` at the start of the line.

```bash title="scripts/run_prepare_benchmark.sh"
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
uv run main.py prepare-benchmark get gaia-val
uv run main.py prepare-benchmark get gaia-val-text-only
uv run main.py prepare-benchmark get frames-test
uv run main.py prepare-benchmark get webwalkerqa
uv run main.py prepare-benchmark get browsecomp-test
uv run main.py prepare-benchmark get browsecomp-zh-test
uv run main.py prepare-benchmark get hle
uv run main.py prepare-benchmark get xbench-ds
uv run main.py prepare-benchmark get futurex
```

### What This Script Does

!!! success "Script Actions"
    1. **Confirms dataset access** - Verifies you have requested access to required datasets
    2. **Downloads benchmark datasets** - Retrieves the following datasets:
        - `gaia-val` - GAIA validation set
        - `gaia-val-text-only` - Text-only GAIA validation
        - `frames-test` - Frames test dataset
        - `webwalkerqa` - Web Walker QA dataset
        - `browsecomp-test` - English BrowseComp test set
        - `browsecomp-zh-test` - Chinese BrowseComp test set
        - `hle` - HLE dataset
        - `xbench-ds` - xbench-DeepSearch dataset
        - `futurex` - Futurex-Online dataset

### Customizing Dataset Selection

To download only specific datasets, edit the script and comment out unwanted lines:

```bash
# Comment out unwanted datasets like this:
# uv run main.py prepare-benchmark get gaia-val
uv run main.py prepare-benchmark get gaia-val-text-only
# uv run main.py prepare-benchmark get frames-test
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI
