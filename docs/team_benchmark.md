# Three-model team benchmark

## Protocol

Evaluate `qwen3:8b`, `llama3.1:8b`, and `gemma3:12b` in separate mixed teams.
Agents 0, 2, and 4 use the selected model; agents 1, 3, and 5 use the classical
planner. These are three team configurations, not three LLM families in one team.

The main campaign uses default-scenario seeds `8000..8011`, with three policies
per model and seed: periodic semantic reporting (`sem`), task-aware MICA (`mica`),
and ideal delivery (`genie`). There are 108 missions. Default MICA parameters
are unchanged: temperature 0.1, no receiver calibration, energy price `1e-5`,
and 100 symbols available per agent per slot. The grid is 32 by 32, with six
agents, eight survivors, and a 400-slot horizon. This benchmark has no training
or parameter fitting. It uses fresh seeds distinct from calibration experiments.

Each policy is evaluated on the same world, sensing, and channel seed. Policy
execution order rotates by seed, and each policy appears first four times per
model. All simulation and orchestration run in WSL Ubuntu 22.04. Windows Ollama
serves the installed models on an RTX 3090 (24 GB) through the existing Python
stdio bridge. Missions execute sequentially to avoid competing GPU workloads.

Generation uses structured choice JSON, `think: false`, temperature 0, seed 0,
1024 context tokens, and 12 output tokens for every model and policy. Exact model
digests, Ollama version, source hash, full configuration, and seeds are stored
per model in `manifest.json`. Resuming with changed settings is rejected.
The context value is the requested setting: Ollama's runtime reports an actual
2048-token allocation for Gemma 3, and 1024 for Qwen3 and Llama 3.1. Prompts fit
within either allocation. Within each model all policies use the same allocation.
An LLM backend fallback immediately stops a mission before it can be recorded.
Unfinished missions without backend failures are retained as unsuccessful runs
with the 400-slot capped completion time, not discarded.

## Metrics

Report mean completion slots, mean uplink symbols, and completion rate over all
scheduled seeds. Smaller slots and symbol counts are better. `genie` bypasses
the wireless delivery mechanism, so its recorded communication counters are not
a comparable physical resource cost and should be displayed as not applicable.
Ideal delivery is not a guaranteed lower bound on task completion time: planners
can make different decisions when they receive more information.

The runner also reports paired MICA-minus-`sem` differences with 10,000 bootstrap
seed resamples. Twelve pairs are exploratory; intervals are unadjusted for
multiple comparisons. They do not establish general superiority across models,
mission layouts, or channel settings.

Own response caches start in the fresh `results/team_benchmark/` directory;
previous experiment caches are not imported. Identical prompts may be reused
within that model's policy runs. Per-mission records include decisions, cache
hits/misses, HTTP requests, token counts, client/server time, and wall time.
Shared caching makes wall time unsuitable as an online inference-speed claim.
Warmup calls are excluded from mission counters.

## Results

Measured on 2026-10-17 with Windows Ollama 0.33.3. All three installed models use
Q4_K_M quantization. Source starts at revision `6d5f812` with the benchmark runner
and scheme-selectable mission instrumentation. The campaign source SHA-256 is
`0989d9062247eaf3c1dbce7bfcbb4caaeb91f54346db637bc97162120fbdbdee`.

All 108 missions completed with all eight survivors found, and zero backend
fallbacks. There were 8,175 LLM decisions: 7,787 online HTTP requests and 388
cache hits, excluding three warmup requests. Each recorded online decision used
exactly one HTTP request; no retries were needed in this cohort. Auditing verified
36 unique records per model, all 12 expected seeds per policy, the same source
hash for all three models, and summary agreement with the raw mission records.

Installed model digests:

| Model | SHA-256 digest |
| --- | --- |
| Qwen3 8B | `500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41` |
| Llama 3.1 8B | `46e0c10c039e019119339687c3c1757cc81b9da49709a3b3924863ba87ca666e` |
| Gemma 3 12B | `b92b218582c521ba287f38f1d6057dcd3c6cbff036f13cac97b5d861f5e58ec3` |

Absolute means over seeds `8000..8011`:

| Model | Policy | Missions | Mean completion slots | Mean uplink symbols | Completion rate |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen3 8B | Periodic semantic | 12 | 81.33 | 42,307.75 | 100% |
| Qwen3 8B | MICA | 12 | 88.50 | 15,336.75 | 100% |
| Qwen3 8B | Ideal reference | 12 | 72.08 | N/A | 100% |
| Llama 3.1 8B | Periodic semantic | 12 | 101.17 | 53,726.33 | 100% |
| Llama 3.1 8B | MICA | 12 | 80.08 | 13,819.92 | 100% |
| Llama 3.1 8B | Ideal reference | 12 | 82.08 | N/A | 100% |
| Gemma 3 12B | Periodic semantic | 12 | 100.67 | 54,086.17 | 100% |
| Gemma 3 12B | MICA | 12 | 69.42 | 12,422.75 | 100% |
| Gemma 3 12B | Ideal reference | 12 | 69.92 | N/A | 100% |

Paired MICA-minus-periodic differences, with exploratory 95% bootstrap intervals:

| Model | Slot difference | Symbol difference |
| --- | --- | --- |
| Qwen3 8B | +7.17 [-6.92, +20.25] | -26,971.00 [-35,302.59, -18,743.76] |
| Llama 3.1 8B | -21.08 [-54.08, +7.17] | -39,906.42 [-58,124.64, -23,746.99] |
| Gemma 3 12B | -31.25 [-65.58, -1.75] | -41,663.42 [-61,032.98, -24,293.85] |

Mean symbol use falls by 63.8%, 74.3%, and 77.0% for Qwen3, Llama, and Gemma,
respectively. The symbol-difference intervals are below zero for all three
models. Mean completion slots change by +8.8%, -20.8%, and -31.0%, respectively.
The Qwen3 and Llama slot intervals include zero; only Gemma's is below zero in
this exploratory cohort. These unadjusted comparisons from 12 seed pairs do not
establish a general task-speed advantage across models or scenarios.

All policies have the same configured per-agent symbol availability, not equal
actual symbol expenditure. The periodic policy's link adaptation and message
selection differ from MICA's, so this is a complete-policy comparison and does
not isolate which module causes the savings. No comparison of LLM model quality
or parameter-count efficiency follows from these mission means.

### Inference accounting

The following counts sum the 12 missions per policy and exclude model warmup.
Cache hits are choices replayed from this campaign's own model-specific cache.
Server seconds cover the actual online requests; they are not a controlled
online-latency comparison.

| Model | Policy | LLM decisions | Cache hits | HTTP requests | Server seconds |
| --- | --- | ---: | ---: | ---: | ---: |
| Qwen3 8B | Periodic semantic | 901 | 66 | 835 | 209.83 |
| Qwen3 8B | MICA | 944 | 24 | 920 | 229.82 |
| Qwen3 8B | Ideal reference | 841 | 40 | 801 | 200.54 |
| Llama 3.1 8B | Periodic semantic | 1,010 | 60 | 950 | 351.23 |
| Llama 3.1 8B | MICA | 807 | 24 | 783 | 291.24 |
| Llama 3.1 8B | Ideal reference | 928 | 39 | 889 | 324.95 |
| Gemma 3 12B | Periodic semantic | 1,131 | 75 | 1,056 | 726.18 |
| Gemma 3 12B | MICA | 768 | 24 | 744 | 580.67 |
| Gemma 3 12B | Ideal reference | 845 | 36 | 809 | 607.09 |

Model weights were not modified. This campaign does not use the optional
receiver-calibration vectors. Its main result tables are independent of the
earlier softmax-calibration studies, which remain documented separately.

## Reproduce

For within-seed model comparisons and backend composition advice, see
[model selection](model_selection.md). The present means do not establish a
stable model ranking. The [figure workflow](figures.md) rebuilds task/resource
plots and paired model contrasts from local raw data or the public source CSV.

```bash
python -m experiments.run_team_benchmark --seeds 12 \
  --windows-python /mnt/c/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe
```

With an endpoint directly accessible from the simulation host, omit
`--windows-python` and optionally provide `--url http://HOST:11434`.
All three tags must already be installed. Generated manifests, JSONL mission
records, response caches, and JSON summaries are local and ignored by Git.

Use `--scenarios` to select additional mission layouts or link settings, and use
a new `--output` directory whenever changing source or campaign settings.
