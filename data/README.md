# Data Directory

This directory contains evaluation datasets used for testing and benchmarking.

## Dataset Download Instructions

### Prerequisites

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

### Download and Prepare Datasets

Once you have been granted access to the required datasets, run the following script to download and prepare all benchmark datasets:

```bash
bash scripts/run_prepare_benchmark.sh
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