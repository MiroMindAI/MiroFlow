# Prepare Official Benchmark Datasets

# - Coming Soon -


---
**Last Updated:** Sep 2025  
**Doc Contributor:** Team @ MiroMind AI


# - - - - - - - - - - - - - - - - - - - - - -
# - The followings are kept for future references -


### Evaluate on Benchmark

Prepare datasets according to your requirements. Some datasets may need to be downloaded manually into the `/data/<benchmark>` folder, and you should also create a corresponding `standardized_data.jsonl` metafile. We will support as many datasets as possible as soon as we can.
```bash
## supported benchmarks
cd MiroFlow/apps/prepare-benchmark
uv run main.py get gaia-val
uv run main.py get browsecomp-test
uv run main.py get browsecomp-zh-test
uv run main.py get hle
```

Run evaluation using the default settings. (Not parallelized; not recommended.)
```bash
## run the code
cd MiroFlow/apps/run-agent
uv run main.py common-benchmark benchmark=gaia-validation
uv run main.py common-benchmark benchmark=browsecomp
uv run main.py common-benchmark benchmark=browsecomp-zh
uv run main.py common-benchmark benchmark=hle
```

For parallel and multi-run evaluations, and to gain better control over environment settings using Hydra, **we recommend using the provided script**:

```bash
cd MiroFlow/apps/run-agent
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_gaia-validation.sh
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_browsecomp.sh
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_browsecomp-zh.sh
bash ./scripts/main-worker-dual/run_evaluate_multiple_runs_hle.sh
```

You can easily modify and customize these scripts to suit your needs. See [Customized Configuration](#customized-configuration) for more details.


