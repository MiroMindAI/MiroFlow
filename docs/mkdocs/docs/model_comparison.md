# Model Comparison Leaderboard

> **Same tools. Same prompts. Same infrastructure. The only variable is the model.**

MiroFlow provides a standardized evaluation environment where every model gets the same tools, the same prompt templates, and the same infrastructure. This makes cross-model comparison fair and reproducible.

---

## Cross-Model Performance

All results below were produced using MiroFlow with identical configurations — only `provider_class` and `model_name` differ.

| Benchmark | MiroThinker 1.5 | Claude 3.7 Sonnet | Kimi K2.5 |
|-----------|-----------------|-------------------|-----------|
| GAIA Validation (165) | **82.4%** | 73.9% | — |
| GAIA Text-Only (103) | **79.6%** | — | 52.4% |
| HLE | **27.2%** | — | — |
| HLE Text-Only | **29.5%** | — | — |
| BrowseComp-EN | 33.2% | — | — |
| BrowseComp-ZH | **47.1%** | — | — |
| xBench-DeepSearch | **72.0%** | — | — |
| FutureX | — | — | — |

!!! note "Table Coverage"
    This table only shows model-benchmark combinations with real, reproducible data. As more models are evaluated, new columns and rows will be added. No placeholders — every cell has a verified result.

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

| Model/Framework | GAIA Val | HLE | HLE-Text | BrowseComp-EN | BrowseComp-ZH | xBench-DS |
|----------------|----------|-----|----------|----------------|----------------|-----------|
| **MiroFlow + MiroThinker 1.5** | **82.4%** | **27.2%** | 29.5% | 33.2% | **47.1%** | **72.0%** |
| OpenAI Deep Research | 67.4% | 26.6% | — | **51.5%** | 42.9% | — |
| Gemini Deep Research | — | 26.9% | — | — | — | 50+% |
| Kimi Researcher | — | — | 26.9% | — | — | 69.0% |
| Manus | 73.3% | — | — | — | — | — |
| WebSailor-72B | 55.4% | — | — | — | 30.1% | 55.0% |
| DeepSeek v3.1 | — | — | **29.8%** | — | — | 71.2% |

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
