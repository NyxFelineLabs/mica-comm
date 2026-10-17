# Softmax calibration with LLM teams

This experiment tests receiver-specific temperature and public-target
persistence in teams with LLM planners. It changes only the teammate softmax
predictor used by MICA. It does not fine-tune the language models or modify
their prompts, candidate selection, communication price, or planning interval.

## Protocol

Two separate team configurations use `qwen3:8b` and `llama3.1:8b`, respectively.
Each team has three LLM agents (indices 0, 2, 4) and three classical planners.
Each mission uses one LLM model; multiple LLM families are not mixed within a
single team. All missions run sequentially on one GPU.

For each model independently, default-scenario training seeds `6000..6007`
provide target labels every five slots. Each receiver's temperature and
persistence minimize target negative log-likelihood on that training set using
the same grid as the [classical calibration experiment](behavior_calibration.md).
All six receivers are calibrated, including the classical agents. Private
targets are offline supervised labels only; runtime prediction uses public
information. This procedure assumes access to instrumented training targets.
Samples include targets retained between LLM replans. This campaign compares
baseline with combined calibration; it does not separately ablate temperature
and persistence in LLM teams.

Parameters are frozen before paired evaluation on seeds `7000..7011` in the
default and clustered scenarios. There are 48 evaluation missions per model,
96 across both models, plus 16 training missions. Arm execution order alternates
by seed. Seeds fix mission randomness; the two arms can follow different paths.

Report completion rate, completion slots, and uplink symbols. Paired bootstrap
intervals use 10,000 seed resamples. These are exploratory, unadjusted intervals
from only 12 pairs per comparison, not a confirmatory significance claim.
Prediction NLL uses the held-out **baseline** trajectories and is reported
separately for LLM and classical receivers. A prediction improvement alone does
not establish better task outcomes.

## Inference and cache controls

Both arms use Ollama structured JSON, temperature 0, seed 0, context 1024,
12 output tokens, and `think: false`. Disabling thinking allows Qwen3 to return
the short choice within this budget. Neither arm receives extra reasoning
tokens. The models themselves are unchanged.

The runner requires the exact tags to be installed, records model digests and
the simulator/runner source hash, and refuses to resume with a different
protocol. Use a new output directory after source or setting changes. An LLM
backend fallback stops the mission immediately; it cannot silently substitute
a classical planner in the recorded sample.

Own response caches start in a new output directory, isolated from previous
experiments. Training and paired evaluations share that model's new cache.
Identical prompts may therefore be replayed. Per-mission records include cache
hits, misses, HTTP requests, client and Ollama server time, prompt/output token
counts, wall time, and fallback counts. Server time covers online cache misses.
These timings describe execution cost, **not a controlled comparison of online
inference latency**, because cache reuse depends on arm order and trajectory.
Simulated completion slots are a separate metric.

The full-grid softmax predictor remains an approximation of a planner that
chooses among five candidates and sometimes retains its target. This experiment
does not change that candidate mechanism, establish causal message-response
accuracy, or compare at equal actual symbol use.

## Run

With an accessible local Ollama endpoint:

```bash
python -m experiments.run_llm_calibration
```

When WSL cannot reach Windows Ollama bound to Windows localhost, use its existing
Windows Python through a persistent stdin/stdout bridge:

```bash
python -m experiments.run_llm_calibration \
  --windows-python /mnt/c/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe
```

The bridge uses local HTTP without system proxy detection and opens no listening
port. Change the executable path to match the machine. The simulation and
calibration still execute in WSL. For a network endpoint use `--url` with an
Ollama base URL, without `/api/generate`.

Model-specific manifests, training labels, frozen parameters, evaluation records,
response caches, and summaries are under `results/llm_behavior_calibration/`.
The directory is ignored by Git. Full replay from the generated cache preserves
task metrics but does not reproduce original online timings.

See [measured results](llm_behavior_calibration_results.md) for outcomes,
prediction diagnostics, inference accounting, and the observed resource tradeoff.
