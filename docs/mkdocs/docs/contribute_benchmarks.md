# 🧪 Adding New Benchmarks to MiroFlow

This guide provides a comprehensive walkthrough for adding new benchmarks to the MiroFlow framework. MiroFlow uses a modular benchmark architecture that allows for easy integration of new evaluation datasets.

---

## 🚀 Step-by-Step Implementation Guide

### Step 1: Prepare Your Dataset

Your benchmark dataset should follow this structure:

```
your-benchmark/
├── standardized_data.jsonl    # Metadata file (required)
├── file1.pdf                  # Optional: Binary files referenced by tasks
├── file2.png
└── ...
```

#### Metadata Format (JSONL)

Each line in `standardized_data.jsonl` should be a JSON object with these fields:

```json
{
  "task_id": "unique_task_identifier",
  "task_question": "The question or instruction for the task",
  "ground_truth": "The expected answer or solution",
  "file_path": "path/to/file.pdf",  // Optional, can be null
  "metadata": {                     // Optional, can be empty
    "difficulty": "hard",
    "category": "reasoning",
    "source": "original_dataset_name"
  }
}
```

**Example:**
```json
{
  "task_id": "math_001",
  "task_question": "What is the integral of x^2 from 0 to 2?",
  "ground_truth": "8/3",
  "file_path": null,
  "metadata": {
    "difficulty": "medium",
    "category": "calculus"
  }
}
```

### Step 2: Create Configuration File

Create a new configuration file in `config/benchmark/your-benchmark.yaml`:

```yaml
# config/benchmark/your-benchmark.yaml
defaults:
  - default
  - _self_

name: "your-benchmark"

data:
  data_dir: "${data_dir}/your-benchmark"  # Path to your dataset
  metadata_file: "standardized_data.jsonl"  # Metadata filename
  whitelist: []  # Optional: List of specific task_ids to run

execution:
  max_tasks: null      # null = no limit, or specify a number
  max_concurrent: 5    # Number of parallel tasks
  pass_at_k: 1         # Number of attempts per task

openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
```

### Step 3: Set Up Data Directory

Place your dataset in the appropriate data directory:

```bash
# Create the benchmark data directory
mkdir -p data/your-benchmark

# Copy your dataset files
cp your-dataset/* data/your-benchmark/
```

### Step 4: Test Your Benchmark

Run your benchmark using the MiroFlow CLI:

```bash
# Test with a small subset 
uv run main.py common-benchmark \
  --config_file_name=agent_quickstart_1 \
  benchmark=your-benchmark \
  benchmark.execution.max_tasks=5 \
  output_dir=logs/test-your-benchmark
```

---

**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI
