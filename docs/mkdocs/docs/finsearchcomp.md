# FinSearchComp

MiroFlow's evaluation on the FinSearchComp benchmark demonstrates capabilities in financial information search and analysis tasks, showcasing advanced reasoning abilities in complex financial research scenarios.

More details: [FinSearchComp Dataset](https://huggingface.co/datasets/ByteSeedXpert/FinSearchComp)

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
    This section provides step-by-step instructions to run the FinSearchComp benchmark and prepare submission results. **Note**: This is a quick start guide for running the benchmark, not for reproducing exact submitted results.

### Step 1: Prepare the FinSearchComp Dataset

!!! tip "Dataset Setup"
    Use the integrated prepare-benchmark command to download and process the dataset:

```bash title="Download FinSearchComp Dataset"
uv run main.py prepare-benchmark get finsearchcomp
```

This will create the standardized dataset at `data/finsearchcomp/standardized_data.jsonl`.

### Step 2: Configure API Keys

!!! warning "API Key Configuration"
    Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```env title=".env Configuration"
# For searching and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# For Linux sandbox (code execution environment)
E2B_API_KEY="xxx"

# We use MiroThinker model for financial analysis
OAI_MIROTHINKER_API_KEY="xxx"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# Used for hint generation and final answer extraction
OPENAI_API_KEY="xxx"
OPENAI_BASE_URL="https://api.openai.com/v1"

# Used for Claude vision understanding
ANTHROPIC_API_KEY="xxx"

# Used for Gemini vision
GEMINI_API_KEY="xxx"
```

### Step 3: Run the Evaluation

!!! example "Evaluation Execution"
    Execute the following command to run evaluation on the FinSearchComp dataset:

```bash title="Run FinSearchComp Evaluation"
uv run main.py common-benchmark --config_file_name=agent_finsearchcomp benchmark=finsearchcomp output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Progress Monitoring and Resume"
    To check the progress while running:
    
    ```bash title="Check Progress"
    uv run utils/progress_check/check_finsearchcomp_progress.py $PATH_TO_LOG
    ```
    
    If you need to resume an interrupted evaluation, specify the same output directory to continue from where you left off.

    ```bash title="Resume Evaluation, e.g."
    uv run main.py common-benchmark --config_file_name=agent_finsearchcomp benchmark=finsearchcomp output_dir=${PATH_TO_LOG}
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

!!! info "Output Analysis"
    The evaluation generates detailed execution traces showing:

    - Research process for each financial task
    - Information gathering from multiple sources
    - Financial calculations and analysis
    - Comprehensive reports with insights and recommendations

### Directory Structure

After running evaluations, you'll find the following structure:

```
logs/finsearchcomp/agent_finsearchcomp_YYYYMMDD_HHMM/
├── benchmark_results.jsonl              # Task results summary
├── benchmark_results_pass_at_1_accuracy.txt  # Accuracy statistics
├── task_(T1)Time_Sensitive_Data_Fetching_*.json  # T1 task traces
├── task_(T2)Financial_Analysis_*.json   # T2 task traces
├── task_(T3)Complex_Historical_Investigation_*.json  # T3 task traces
└── output.log                           # Execution log
```

### Task Categories Breakdown

The progress checker provides detailed statistics:

- **Total Tasks**: Complete count across all categories
- **Completed Tasks**: Successfully finished tasks
- **Correct Tasks**: Tasks with judge_result "CORRECT" (T2 and T3 only)
- **Category Breakdown**: Separate counts for T1, T2, and T3 tasks
- **Accuracy Metrics**: Pass@1 accuracy for evaluable tasks

---

## Usage Examples

### Single Run Evaluation
```bash title="Basic Evaluation"
uv run main.py common-benchmark --config_file_name=agent_finsearchcomp benchmark=finsearchcomp output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

### Limited Task Testing
```bash title="Test with Limited Tasks"
uv run main.py common-benchmark --config_file_name=agent_finsearchcomp benchmark=finsearchcomp benchmark.execution.max_tasks=5 output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

### Custom Agent Configuration
```bash title="Different Agent Setup"
uv run main.py common-benchmark --config_file_name=agent_gaia-validation benchmark=finsearchcomp output_dir="logs/finsearchcomp/$(date +"%Y%m%d_%H%M")"
```

### Multiple Runs for Reliability
```bash title="Multiple Runs"
NUM_RUNS=5 ./scripts/run_evaluate_multiple_runs_finsearchcomp.sh
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI
