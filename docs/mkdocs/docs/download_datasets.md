# Dataset Download Instructions

## Prerequisites

Before downloading the datasets, you need to:

1. **Request access to Hugging Face datasets**:
   - **GAIA Dataset**: https://huggingface.co/datasets/gaia-benchmark/GAIA
   - **HLE Dataset**: https://huggingface.co/datasets/cais/hle

   Please visit these links and request access to the datasets.

2. **Configure environment variables**:

   Copy the template file and create your environment configuration:
   ```bash
   cp .env.template .env
   ```

   Then edit the `.env` file and configure these two essential variables:

   ```env
   # Required: Your Hugging Face token for dataset access
   HF_TOKEN="your-actual-huggingface-token-here"
   
   # Data directory path 
   DATA_DIR="data/"
   ```

   To get your Hugging Face token:
   - Go to https://huggingface.co/settings/tokens
   - Create a new token with "Read" permissions
   - Replace `<your-huggingface-token>` in the `.env` file with your actual token

## Download and Prepare Datasets

Once you have been granted access to the required datasets, run the script `bash scripts/run_prepare_benchmark.sh` shown below to download and prepare all benchmark datasets. You may comment out any unwanted datasets:

```
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
```
This script will:
1. Confirm that you have access to the required datasets
2. Download and prepare the following benchmark datasets:
   - gaia-val
   - gaia-val-text-only
   - frames-test
   - webwalkerqa
   - browsecomp-test
   - browsecomp-zh-test
   - hle


---
**Last Updated:** Sep 2025  
**Doc Contributor:** Index @ MiroMind AI