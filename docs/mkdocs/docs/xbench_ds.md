# xbench-DeepSearch

The **xbench** benchmark is an evaluation framework designed to measure both the intelligence frontier and real-world utility of AI agents. It consists of complementary tracks that test core model capabilities like reasoning, tool use, memory, and workflows grounded in business and professional settings. Its **DeepSearch** sub-track measures agents' ability to conduct open-domain information retrieval, combining fact finding, comparison, and synthesis through multi-step search and tool use.

See more details at [xbench official website](https://xbench.org/agi/aisearch) and [xbench-DeepSearch Eval Card](https://xbench.org/files/Eval%20Card%20xbench-DeepSearch.pdf).


---

## Setup and Evaluation Guide

### Step 1: Download the xbench-DeepSearch Dataset

!!! tip "Dataset Setup"
    Use the integrated prepare-benchmark command to download and process the dataset:

```bash
uv run -m src.utils.prepare_benchmark.main get xbench-ds
```

By default, this will create the standardized dataset at data/xbench-ds/standardized_data.jsonl.

### Step 2: Configure API Keys

!!! warning "Required API Configuration"
    Set up the required API keys for model access and tool functionality. Update the `.env` file to include the following keys:

```env title=".env Configuration"
# MiroThinker model access
OAI_MIROTHINKER_API_KEY="your-mirothinker-api-key"
OAI_MIROTHINKER_BASE_URL="http://localhost:61005/v1"

# Search and web scraping capabilities
SERPER_API_KEY="your-serper-api-key"
JINA_API_KEY="your-jina-api-key"

# Code execution environment
E2B_API_KEY="your-e2b-api-key"
```

### Step 3: Run the Evaluation

```bash title="Run xbench-DeepSearch Evaluation with MiroThinker"
uv run src/benchmark/run_benchmark.py \
  --config-path config/standard_xbench-ds_mirothinker.yaml \
  benchmark.execution.max_concurrent=30 \
  output_dir="logs/xbench-ds/$(date +"%Y%m%d_%H%M")"
```

### Step 4: Monitor Progress and Resume

!!! tip "Progress Tracking"
    You can monitor the evaluation progress in real-time:

```bash title="Check Progress"
uv run utils/check_progress_xbench-ds.py $PATH_TO_LOG
```

Replace `$PATH_TO_LOG` with your actual output directory path.

!!! note "Resume Capability"
    If the evaluation is interrupted, you can resume from where it left off by specifying the same output directory.

---

## Multiple Runs and Post-Processing

!!! tip "Test-Time Scaling for Improved Reliability"
    Test-time scaling can significantly improve the reliability of model responses. Instead of simple majority voting, we employ a comprehensive **parallel thinking** approach that:

    - Aggregates final summary steps from each agent run before outputting results
    - Uses another agent (o3 by default) to make final decisions based on equivalence and source reliability criteria
    - Provides more robust and accurate final answers

Execute the following command to run multiple xbench-DeepSearch evaluations:

```bash title="Multiple runs (8 runs)"
bash scripts/standard_xbench-ds_mirothinker_8runs.sh
```

### Running Parallel Thinking Analysis alone

After completing evaluations (single or multiple runs), you can apply parallel thinking post-processing to aggregate and generate the final result.

```bash title="Parallel Thinking Post-Processing"
uv run utils/util_llm_parallel_thinking.py \
  --benchmark xbench-ds \
  --results_dir "logs/xbench-ds/20250922_1430"
```

The program automatically reads results from each run in the specified directory and performs aggregated analysis. The final output files are generated in the `results_dir`:

- **`llm_parallel_thinking_Nruns.json`** - Detailed analysis results
- **`llm_parallel_thinking_accuracy_Nruns.txt`** - Final accuracy

Where `N` represents the total number of experimental runs (**minimum of 1**).

---

!!! info "Documentation Info"
    **Last Updated:** February 2026 · **Doc Contributor:** Team @ MiroMind AI
