# Futurex-Online

MiroFlow's evaluation on the Futurex-Online benchmark demonstrates capabilities in future event prediction tasks.

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
uv run main.py prepare-benchmark get futurex
```

This will create the standardized dataset at `data/futurex/standardized_data.jsonl`.

### Step 2: Configure API Keys

!!! warning "API Key Configuration"
    Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```env title=".env Configuration"
# For searching and web scraping
SERPER_API_KEY="xxx"
JINA_API_KEY="xxx"

# For Linux sandbox (code execution environment)
E2B_API_KEY="xxx"

# We use Claude-3.7-Sonnet with OpenRouter backend to initialize the LLM
OPENROUTER_API_KEY="xxx"
OPENROUTER_BASE_URL="https://openrouter.ai/api/v1"

# Used for Claude vision understanding
ANTHROPIC_API_KEY="xxx"

# Used for Gemini vision
GEMINI_API_KEY="xxx"

# Use for llm judge, reasoning, hint generation, etc.
OPENAI_API_KEY="xxx"
OPENAI_BASE_URL="https://api.openai.com/v1"
```

### Step 3: Run the Evaluation

!!! example "Evaluation Execution"
    Execute the following command to run evaluation on the Futurex-Online dataset. This uses the basic `agent_quickstart_reading` configuration for quick start purposes.

```bash title="Run Futurex-Online Evaluation"
uv run main.py common-benchmark --config_file_name=agent_quickstart_reading benchmark=futurex output_dir="logs/futurex/$(date +"%Y%m%d_%H%M")"
```

!!! tip "Progress Monitoring and Resume"
    To check the progress while running:
    
    ```bash title="Check Progress"
    uv run utils/progress_check/check_futurex_progress.py $PATH_TO_LOG
    ```
    
    If you need to resume an interrupted evaluation, specify the same output directory to continue from where you left off.

    ```bash title="Resume Evaluation, e.g."
    uv run main.py common-benchmark --config_file_name=agent_quickstart_reading benchmark=futurex output_dir="logs/futurex/20250918_1010"
    ```

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

## Multiple Runs and Voting

!!! tip "Improving Prediction Accuracy"
    For better prediction accuracy, you can run multiple evaluations and use voting mechanisms to aggregate results. This approach helps reduce randomness and improve the reliability of predictions. **Note**: This is a quick start approach; production submissions may use more sophisticated configurations.

### Step 1: Run Multiple Evaluations

Use the multiple runs script to execute several independent evaluations:

```bash title="Run Multiple Evaluations"
./scripts/run_evaluate_multiple_runs_futurex.sh
```

This script will:

- Run 3 independent evaluations by default (configurable with `NUM_RUNS`)
- Execute all tasks in parallel for efficiency
- Generate separate result files for each run in `run_1/`, `run_2/`, etc.
- Create a consolidated `futurex_submission.jsonl` file with voting results

### Step 2: Customize Multiple Runs

You can customize the evaluation parameters:

```bash title="Custom Multiple Runs"
# Run 5 evaluations with limited tasks for testing
NUM_RUNS=5 MAX_TASKS=10 ./scripts/run_evaluate_multiple_runs_futurex.sh

# Use different agent configuration
AGENT_SET=agent_gaia-validation ./scripts/run_evaluate_multiple_runs_futurex.sh

# Adjust concurrency for resource management
MAX_CONCURRENT=3 ./scripts/run_evaluate_multiple_runs_futurex.sh
```

### Step 3: Voting and Aggregation

After multiple runs, the system automatically:

1. **Extracts predictions** from all runs using `utils/extract_futurex_results.py`
2. **Applies majority voting** to aggregate predictions across runs
3. **Generates submission file** in the format required by FutureX platform
4. **Provides voting statistics** showing prediction distribution across runs

The voting process works as follows:

- **Majority Vote**: Most common prediction across all runs wins
- **Tie-breaking**: If tied, chooses the prediction that appeared earliest across all runs
- **Vote Counts**: Tracks how many runs predicted each option
- **Confidence Indicators**: High agreement indicates more reliable predictions

### Step 4: Analyze Voting Results

Check the generated files for voting analysis:

```bash title="Check Voting Results"
# View submission file with voting results
cat logs/futurex/agent_quickstart_reading_*/futurex_submission.jsonl

# Check individual run results
ls logs/futurex/agent_quickstart_reading_*/run_*/

# Check progress and voting statistics
uv run python utils/progress_check/check_futurex_progress.py logs/futurex/agent_quickstart_reading_*
```

### Manual Voting Aggregation

You can also manually run the voting aggregation:

```bash title="Manual Voting Aggregation"
# Aggregate multiple runs with majority voting
uv run python utils/extract_futurex_results.py logs/futurex/agent_quickstart_reading_* --aggregate

# Force single run mode (if needed)
uv run python utils/extract_futurex_results.py logs/futurex/agent_quickstart_reading_*/run_1 --single

# Specify custom output file
uv run python utils/extract_futurex_results.py logs/futurex/agent_quickstart_reading_* -o my_voted_predictions.jsonl
```

### Voting Output Format

The voting aggregation generates a submission file with the following format:

```json
{"id": "687104310a994c0060ef87a9", "prediction": "No", "vote_counts": {"No": 2}}
{"id": "68a9b46e961bd3003c8f006b", "prediction": "Yes", "vote_counts": {"Yes": 2}}
```

The output includes:

- **`id`**: Task identifier
- **`prediction`**: Final voted prediction (without `\boxed{}` wrapper)
- **`vote_counts`**: Dictionary showing how many runs predicted each option

For example, `"vote_counts": {"No": 2}` means 2 out of 2 runs predicted "No", indicating high confidence.

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

### Directory Structure

After running multiple evaluations, you'll find the following structure:

```
logs/futurex/agent_quickstart_reading_YYYYMMDD_HHMM/
├── futurex_submission.jsonl          # Final voted predictions
├── run_1/                            # First run results
│   ├── benchmark_results.jsonl       # Individual task results
│   ├── benchmark_results_pass_at_1_accuracy.txt
│   └── task_*_attempt_1.json        # Detailed execution traces
├── run_2/                            # Second run results
│   └── ... (same structure as run_1)
├── run_1_output.log                  # Run 1 execution log
└── run_2_output.log                  # Run 2 execution log
```

---

!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI
