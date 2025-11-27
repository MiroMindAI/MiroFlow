# Web Monitoring Guide for Benchmark Evaluation

This document provides guidance for using the web monitoring dashboard while evaluating benchmarks with MiroFlow.

## Overview

The web monitoring system provides real-time progress tracking, statistics, and task reports through a web interface. It runs alongside the benchmark evaluation process.

## Architecture

```txt
run_benchmark_with_monitor.py (Wrapper)
  ├─> Process 1: common_benchmark.py (Executor)
  │    └─> Executes tasks and generates log files
  │
  └─> Process 2: benchmark_monitor.py (Monitor)
       └─> Reads log files and displays monitoring interface
       └─> Generates task reports via generate_benchmark_report.py
```

## Features

- **Real-time Dashboard**: Monitor progress, statistics, and task status in real-time
- **Web Interface**: Access dashboard at `http://localhost:8080` (or next available port)
- **Task Reports**: View detailed reports for individual tasks
- **Benchmark-Specific Metrics**: Tailored statistics for different benchmark types (GAIA, FutureX, FinSearchComp, xBench)
- **Auto-refresh**: Dashboard updates automatically every 30 seconds

## Supported Benchmarks

`run_benchmark_with_monitor.py` currently supports the following benchmark evaluations:

- **GAIA Validation**
- **FutureX**
- **FinSearchComp**
- **xBench-DeepSearch**

## Usage Examples

#### GAIA Benchmark

```bash
uv run main.py run-benchmark-with-monitor \
  --config_file_name=agent_gaia-validation_claude37sonnet \
  --output_dir="logs/gaia-validation-claude37sonnet/$(date +"%Y%m%d_%H%M")"
```

#### FutureX Benchmark

```bash
uv run main.py run-benchmark-with-monitor \
  --config_file_name=agent_quickstart_reading \
  benchmark=futurex \
  --output_dir="logs/futurex/$(date +"%Y%m%d_%H%M")"
```

#### FinSearchComp Benchmark

```bash
uv run main.py run-benchmark-with-monitor \
  --config_file_name=agent_finsearchcomp_claude37sonnet \
  --output_dir="logs/finsearchcomp-claude37sonnet/$(date +"%Y%m%d_%H%M")"
```

#### xBench-DeepSearch Benchmark

```bash
uv run main.py run-benchmark-with-monitor \
  --config_file_name=agent_xbench-ds_claude37sonnet \
  benchmark=xbench-ds \
  --output_dir="logs/xbench-ds/$(date +"%Y%m%d_%H%M")"
```

💡 To resume an interrupted evaluation, simply replace the output directory with an existing log directory.

