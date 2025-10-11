# Contributing New Benchmarks to MiroFlow

This comprehensive guide walks you through adding new evaluation benchmarks to the MiroFlow framework. MiroFlow's modular architecture makes it easy to integrate diverse evaluation datasets while maintaining consistency and reproducibility.

## Overview

!!! info "Why Add New Benchmarks?"
    Adding new benchmarks serves multiple purposes:
    
    - **Internal Testing**: Validate your agent's performance on custom tasks and domains specific to your use case
    - **Development Iteration**: Create targeted test sets to debug and improve specific agent capabilities
    - **Domain-Specific Evaluation**: Test agents on proprietary or specialized datasets relevant to your application
    - **Research Contributions**: Expand MiroFlow's benchmark coverage to advance the field with new evaluation paradigms
    - **Comparative Analysis**: Benchmark your agent against custom baselines or competitors

## Step-by-Step Implementation Guide

### Step 1: Prepare Your Dataset

Your benchmark dataset must follow MiroFlow's standardized structure for seamless integration.

#### Required Directory Structure

```
your-benchmark/
├── standardized_data.jsonl    # Metadata file (required)
├── file1.pdf                  # Optional: Binary files referenced by tasks
├── file2.png                  # Optional: Images, documents, etc.
├── data.csv                   # Optional: Additional data files
└── ...                        # Any other supporting files
```

#### Metadata Format Specification

Each line in `standardized_data.jsonl` must be a valid JSON object with the following schema:

!!! example "Required Fields"
    ```json
    {
      "task_id": "unique_task_identifier",
      "task_question": "The question or instruction for the task",
      "ground_truth": "The expected answer or solution",
      "file_path": "path/to/file.pdf",  // Optional, can be null
      "metadata": {                     // Optional, can be empty object or other structure
        "difficulty": "hard",
        "category": "reasoning",
        "source": "original_dataset_name"
      }
    }
    ```


#### Example Tasks

**Simple Text-Only Task:**
```json
{
  "task_id": "math_001",
  "task_question": "What is the integral of x^2 from 0 to 2?",
  "ground_truth": "8/3",
  "file_path": null,
  "metadata": {
    "difficulty": "medium",
    "category": "calculus",
    "source": "custom_math_problems"
  }
}
```

**File-Based Task:**
```json
{
  "task_id": "doc_analysis_001",
  "task_question": "Based on the provided financial report, what was the company's revenue growth rate?",
  "ground_truth": "12.5%",
  "file_path": "reports/financial_q3_2023.pdf",
  "metadata": {
    "difficulty": "hard",
    "category": "document_analysis",
    "file_type": "pdf"
  }
}
```

### Step 2: Create Benchmark Configuration

Create a configuration file to define how MiroFlow should handle your benchmark.

#### Configuration File Location

Create: `config/benchmark/your-benchmark.yaml`

#### Configuration Template

```yaml title="config/benchmark/your-benchmark.yaml"
# Benchmark configuration for your custom dataset
defaults:
  - default          # Use default benchmark settings
  - _self_           # Allow overrides in this file

name: "your-benchmark"

data:
  data_dir: "${data_dir}/your-benchmark"        # Dataset location
  metadata_file: "standardized_data.jsonl"     # Metadata filename

execution:
  max_tasks: null          # null = no limit, number = max tasks to run
  max_concurrent: 5        # Number of parallel task executions
  pass_at_k: 1             # Number of attempts per task for pass@k evaluation

# LLM judge configuration for evaluation
openai_api_key: "${oc.env:OPENAI_API_KEY,???}"
```

#### Configuration Options

!!! tip "Execution Parameters"
    - **max_tasks**: Control dataset size during development (use small numbers for testing)
    - **max_concurrent**: Balance speed vs. resource usage
    - **pass_at_k**: Enable multiple attempts for better success measurement

### Step 3: Set Up Data Directory

Organize your dataset files in the MiroFlow data structure.

```bash title="Data Directory Setup"
# Create the benchmark data directory
mkdir -p data/your-benchmark

# Copy your dataset files
cp your-dataset/* data/your-benchmark/

# Verify the structure
ls -la data/your-benchmark/
```

!!! warning "File Path Consistency"
    Ensure that all `file_path` entries in your JSONL metadata correctly reference files in your data directory.

### Step 4: Test Your Benchmark

Validate your benchmark integration with comprehensive testing.

#### Initial Testing

Start with a small subset to verify everything works correctly:

```bash title="Test Benchmark Integration"
uv run main.py common-benchmark \
  --config_file_name=agent_quickstart_reading \
  benchmark=your-benchmark \
  benchmark.execution.max_tasks=3 \
  output_dir="logs/test-your-benchmark/$(date +"%Y%m%d_%H%M")"
```

#### Full Evaluation

Once testing passes, run the complete benchmark:

```bash title="Run Full Benchmark"
uv run main.py common-benchmark \
  --config_file_name=agent_quickstart_reading \
  benchmark=your-benchmark \
  output_dir="logs/your-benchmark/$(date +"%Y%m%d_%H%M")"
```

### Step 5: Validate Results

Review the evaluation outputs to ensure proper integration:

#### Check Output Files

```bash title="Verify Results"
# List generated files
ls -la logs/your-benchmark/

# Review a sample task log
cat logs/your-benchmark/task_*_attempt_1.json | head -50
```

#### Expected Output Structure

Your benchmark should generate:

- Individual task execution logs
- Aggregate benchmark results (`benchmark_results.jsonl`)
- Accuracy summary files
- Hydra configuration logs


!!! info "Documentation Info"
    **Last Updated:** September 2025 · **Doc Contributor:** Team @ MiroMind AI