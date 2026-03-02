# Evaluation Methodology

MiroFlow provides a standardized evaluation framework for fair, reproducible model comparison across 9+ benchmarks. For cross-model results, see the [Model Comparison Leaderboard](model_comparison.md).

---

## Featured Results: MiroThinker

<div align="center" markdown="1">
  ![MiroThinker Performance](assets/mirothinker.png){ width="100%" }
</div>

<div align="center" markdown="1">
  ![BrowseComp MiroThinker Performance](assets/bc-mirothinker.png){ width="100%" }
</div>

---

## Supported Benchmarks

| Benchmark | Category | Verifier Type | Metrics |
|-----------|----------|--------------|---------|
| GAIA (Validation + Test) | General Agent | Exact match + normalization | Pass@1 accuracy |
| HLE / HLE Text-Only | Language Understanding | LLM judge | Accuracy |
| BrowseComp (EN + ZH) | Web Search | Exact match | Accuracy |
| xBench-DeepSearch | Deep Search | Exact match | Accuracy |
| FutureX | Future Prediction | Custom verifier | Ranking |
| FinSearchComp | Finance | Custom verifier | Accuracy |
| WebWalkerQA | Web Navigation | Exact match | Accuracy |
| FRAMES-Test | Multi-hop QA | LLM judge | Accuracy |
| SimpleQA | Simple QA | Exact match | Accuracy |

---

## Controlled Variables

Every benchmark evaluation in MiroFlow controls the following variables to ensure fair comparison:

| Variable | How It's Controlled |
|----------|-------------------|
| **MCP Tools** | Identical tool configurations across all models — same search, code sandbox, file reading, etc. |
| **Prompt Templates** | Same YAML + Jinja2 templates rendered with the same context variables |
| **Verifiers** | Each benchmark has a dedicated verifier implementation used for all models |
| **IO Pipeline** | Same input preprocessing (file content, hints, message formatting) and output extraction (summary, boxed answer) |
| **Rollback Logic** | Same error recovery parameters (`max_consecutive_rollbacks`, `max_duplicate_rollbacks`) |

---

## Multi-Run Evaluation

Benchmark scripts support automated multi-run evaluation for statistical reliability:

1. **Parallel execution**: Multiple evaluation runs execute concurrently
2. **Result aggregation**: Scores are collected and aggregated automatically
3. **Statistical reporting**: Mean, standard deviation, min/max across runs

Example benchmark script:
```bash
# Runs 8 evaluation passes on GAIA validation with MiroThinker
bash scripts/benchmark/mirothinker/gaia-validation-165_mirothinker_8runs.sh
```

---

## Reproduce Results

Follow the benchmark-specific guides in the sidebar to reproduce each result. Each guide includes dataset preparation, configuration, and execution steps.

See the [Model Comparison Leaderboard](model_comparison.md) for cross-model results and framework comparison.
