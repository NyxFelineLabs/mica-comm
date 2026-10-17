# Public mission outcomes

This is a compact snapshot of our measured 108-mission campaign, not author
model-response caches. `missions.csv` preserves every model/policy/seed cell,
completion status, capped completion time, uplink symbol count and fallback
count. Original per-model manifests preserve source/configuration/model hashes
and generation settings. The campaign protocol and inference accounting are
documented in [team benchmark](../../team_benchmark.md).

Rebuild without contacting Ollama:

```bash
python -m experiments.plot_team_benchmark --input docs/data/team_benchmark
```

This reproduces outcome statistics and figures, not new LLM inference. It does
not contain prompts, model responses or per-request timings; those remain in
local raw records. Ideal-delivery symbol counters are retained for traceability
but are displayed as not applicable in physical-cost summaries and plots.
