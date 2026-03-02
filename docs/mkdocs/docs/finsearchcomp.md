# FinSearchComp

MiroFlow's evaluation on the FinSearchComp benchmark demonstrates capabilities in financial information search and analysis tasks, showcasing advanced reasoning abilities in complex financial research scenarios.

More details: [FinSearchComp: Towards a Realistic, Expert-Level Evaluation of Financial Search and Reasoning](https://arxiv.org/abs/2509.13160)

---

## Dataset Overview

!!! info "FinSearchComp Dataset"
    The FinSearchComp dataset consists of financial search and analysis tasks that require comprehensive research capabilities including:

    - Financial data retrieval and analysis
    - Market research and company analysis
    - Investment decision support
    - Financial news and report interpretation
    - Time-sensitive financial information gathering

!!! abstract "Key Dataset Characteristics"

    - **Total Tasks**: 635 (across T1, T2, T3 categories)
    - **Task Types**:
        - **T1**: Time-Sensitive Data Fetching
        - **T2**: Financial Analysis and Research
        - **T3**: Complex Historical Investigation
    - **Answer Format**: Detailed financial analysis and research reports
    - **Ground Truth**: Available for T2 and T3 tasks, changes dynamically for T1 tasks
    - **Evaluation**: Judge-based evaluation with correctness assessment

---

## Quick Start Guide

!!! note "Quick Start Instructions"
    This section provides step-by-step instructions to run the FinSearchComp benchmark and prepare submission results.

### Step 1: Prepare the FinSearchComp Dataset

!!! tip "Dataset Setup"
    Use the integrated prepare-benchmark command to download and process the dataset:

```bash title="Download FinSearchComp Dataset"
uv run -m miroflow.utils.prepare_benchmark.main get finsearchcomp
```

This will create the standardized dataset at `data/finsearchcomp/standardized_data.jsonl`.

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
    Execute the following command to run evaluation on the FinSearchComp dataset:

```bash title="Run FinSearchComp Evaluation"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_gaia-validation-165_mirothinker.yaml \
  benchmark=finsearchcomp \
  output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Extract Results

!!! example "Result Extraction"
    After evaluation completion, the results are automatically generated in the output directory:

- `benchmark_results.jsonl`: Detailed results for each task
- `benchmark_results_pass_at_1_accuracy.txt`: Summary accuracy statistics
- `task_*_attempt_1.json`: Individual task execution traces

---

## Evaluation Notes

!!! warning "Task Type Considerations"
    The FinSearchComp dataset includes different task types with varying evaluation criteria:

    - **T1 Tasks**: Time-Sensitive Data Fetching tasks are excluded from correctness evaluation due to outdated ground truth, but completion is still tracked
    - **T2 Tasks**: Financial Analysis tasks are evaluated for correctness and quality
    - **T3 Tasks**: Complex Historical Investigation tasks require comprehensive research and analysis

---

## Usage Examples

### Limited Task Testing
```bash title="Test with Limited Tasks"
uv run miroflow/benchmark/run_benchmark.py \
  --config-path config/benchmark_gaia-validation-165_mirothinker.yaml \
  benchmark=finsearchcomp \
  benchmark.execution.max_tasks=5 \
  output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
