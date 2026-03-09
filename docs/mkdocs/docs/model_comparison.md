# Model Comparison Leaderboard

> **Same tools. Same prompts. Same infrastructure. The only variable is the model.**

MiroFlow provides a standardized evaluation environment where every model gets the same tools, the same prompt templates, and the same infrastructure. This makes cross-model comparison fair and reproducible.

---

## Cross-Model Performance

All results below were produced using MiroFlow with identical configurations — only `provider_class` and `model_name` differ.

!!! note "Coming Soon"
    Benchmark results will be updated after comprehensive testing with v1.7. Stay tuned.

---

## Why These Comparisons Are Fair

MiroFlow controls every variable except the model itself:

| Variable | How It's Controlled |
|----------|-------------------|
| **MCP Tools** | All models use the same tool set (search, code sandbox, file reading, etc.) configured via identical YAML files |
| **Prompt Templates** | Same YAML + Jinja2 prompt templates across all models |
| **Verifiers** | Each benchmark uses the same automated verifier (exact match, LLM-judge, or custom) regardless of model |
| **Multi-Run Aggregation** | Results are averaged over multiple runs with statistical reporting (mean, std dev, min/max) |
| **Infrastructure** | Same MCP server configurations, same API retry/rollback logic, same IO processing pipeline |

The framework is the constant. The model is the variable.

---

## Test Your Own Model

Add any OpenAI-compatible model to the leaderboard in three steps:

### Step 1: Create an LLM Client (if needed)

For OpenAI-compatible APIs, use the built-in `OpenAIClient`:

```yaml
llm:
  provider_class: OpenAIClient
  model_name: your-model-name
```

For custom APIs, implement a new client with the `@register` decorator. See [Add New Model](contribute_llm_clients.md).

### Step 2: Copy a Benchmark Config and Change the LLM

```yaml
# Copy any existing benchmark config, e.g.:
# config/benchmark_gaia-validation-165_mirothinker.yaml

# Change only these two lines:
main_agent:
  llm:
    provider_class: OpenAIClient       # Your client
    model_name: your-model-name        # Your model
```

### Step 3: Run the Benchmark

```bash
bash scripts/benchmark/mirothinker/gaia-validation-165_mirothinker_8runs.sh
# (or adapt the script for your config)
```

Results are automatically evaluated by the benchmark verifier and aggregated across runs.

### Step 4 (Optional): Submit a PR

Add your config and results to the repository. We welcome community-contributed model evaluations.

---

## MiroFlow vs Other Frameworks

Coming soon — framework comparison results will be added after v1.7 testing is complete.

---

## Reproduce Any Result

Every result in the tables above can be reproduced from a config file. Follow the benchmark-specific guides:

- **GAIA**: [Prerequisites](gaia_validation_prerequisites.md) · [MiroThinker](gaia_validation_mirothinker.md) · [Claude 3.7](gaia_validation_claude37sonnet.md) · [GPT-5](gaia_validation_gpt5.md) · [Text-Only](gaia_validation_text_only.md)
- **BrowseComp**: [English](browsecomp_en.md) · [Chinese](browsecomp_zh.md)
- **HLE**: [Full](hle.md) · [Text-Only](hle_text_only.md)
- **Other**: [FutureX](futurex.md) · [xBench-DS](xbench_ds.md) · [FinSearchComp](finsearchcomp.md) · [WebWalkerQA](webwalkerqa.md)

---

!!! info "Documentation Info"
    **Last Updated:** March 2026 · **Doc Contributor:** Team @ MiroMind AI
