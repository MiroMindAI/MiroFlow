# Futurex-Online

MiroFlow's evaluation on the Futurex-Online benchmark demonstrates capabilities in future event prediction tasks.

More details: [FutureX: An Advanced Live Benchmark for LLM Agents in Future Prediction](https://arxiv.org/abs/2508.11987)


---

## Dataset Overview

!!! info "Futurex-Online Dataset"
    The Futurex-Online dataset consists of 61 prediction tasks covering various future events including:

    - Political events (referendums, elections)
    - Sports outcomes (football matches)
    - Legal proceedings
    - Economic indicators


!!! abstract "Key Dataset Characteristics"

    - **Total Tasks**: 61
    - **Task Type**: Future event prediction
    - **Answer Format**: Boxed answers (\\boxed{Yes/No} or \\boxed{A/B/C})
    - **Ground Truth**: Not available (prediction tasks)
    - **Resolution Date**: Around 2025-09-21 (GMT+8)

---

## Quick Start Guide

!!! note "Quick Start Instructions"
    This section provides step-by-step instructions to run the Futurex-Online benchmark and prepare submission results. Since this is a prediction dataset without ground truth, we focus on execution traces and response generation. **Note**: This is a quick start guide for running the benchmark, not for reproducing exact submitted results.

### Step 1: Prepare the Futurex-Online Dataset

!!! tip "Dataset Setup"
    Use the integrated prepare-benchmark command to download and process the dataset:

```bash title="Download Futurex-Online Dataset"
uv run -m src.utils.prepare_benchmark.main get futurex
```

This will create the standardized dataset at `data/futurex/standardized_data.jsonl`.

### Step 2: Configure API Keys

!!! warning "API Key Configuration"
    Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```env title=".env Configuration"
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# For searching and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# For code execution (E2B sandbox)
E2B_API_KEY="xxx"
```

### Step 3: Run the Evaluation

!!! example "Evaluation Execution"
    Execute the following command to run evaluation on the Futurex-Online dataset using a standard configuration:

```bash title="Run Futurex-Online Evaluation"
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_gaia-validation-165_mirothinker.yaml \
  benchmark=futurex \
  output_dir="logs/futurex/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Progress Monitoring and Resume"
    If you need to resume an interrupted evaluation, specify the same output directory to continue from where you left off.

### Step 4: Extract Results

!!! example "Result Extraction"
    After evaluation completion, extract the results using the provided utility:

```bash title="Extract Results"
uv run utils/extract_futurex_results.py logs/futurex/$(date +"%Y%m%d_%H%M")
```

This will generate:

- `futurex_results.json`: Detailed results for each task
- `futurex_summary.json`: Summary statistics
- `futurex_predictions.csv`: Predictions in CSV format

---

## Sample Task Examples

### Political Prediction
```
Task: "Will the 2025 Guinea referendum pass? (resolved around 2025-09-21 (GMT+8))"
Expected Format: \boxed{Yes} or \boxed{No}
```

### Sports Prediction
```
Task: "Brighton vs. Tottenham (resolved around 2025-09-21 (GMT+8))
A. Brighton win on 2025-09-20
B. Brighton vs. Tottenham end in a draw
C. Tottenham win on 2025-09-20"
Expected Format: \boxed{A}, \boxed{B}, or \boxed{C}
```

---

## Evaluation Notes

!!! warning "No Ground Truth Available"
    Since Futurex-Online is a prediction dataset, there are no ground truth answers available for evaluation. The focus is on:

    - Response generation quality
    - Reasoning process documentation
    - Prediction confidence and methodology

!!! info "Output Analysis"
    The evaluation generates detailed execution traces showing:

    - Research process for each prediction
    - Information gathering from web sources
    - Reasoning chains leading to predictions
    - Final boxed answers in required format

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
