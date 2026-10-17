# MOSAIC-Comm

MOSAIC-Comm is a small, reproducible simulator for **M**ulti-agent **O**rchestration
and **S**emantic-aware **A**gent **I**nter-agent **C**ommunication. It models
heterogeneous search-and-rescue agents sharing a fading wireless uplink. The
project contains the simulator, the goal-oriented semantic communication (GOSC)
baselines, LLM-driven planners, and the paper experiment runners.

This repository is a cleaned, `src`-layout continuation of the research code for
"Resource-Efficient Semantic Communication for Heterogeneous Agentic Teams".
The original research repository is preserved separately; this project is the
recommended base for new work.

## Quick start

Python 3.9 or newer is supported.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Run one deterministic mission:

```bash
.venv/bin/python -m mosaic_comm.simulator --scheme gosc --seed 0
```

On Windows, use `.venv\\Scripts\\python.exe` in the same commands. The package
is installed in editable mode, so changes under `src/mosaic_comm` are immediately
available to the experiment scripts.

## Experiments

All experiment commands write local output under `results/` and generated plots
under `figures/`; both are ignored by Git.

```bash
.venv/bin/python -m experiments.run_all --seeds 100
.venv/bin/python -m experiments.plot
.venv/bin/python -m experiments.run_joint --seeds 100
```

The larger paper campaign is described in [docs/reproduction.md](docs/reproduction.md).
Start with a small seed count while developing a change.

## Optional Ollama backend

LLM agents use Ollama only when an experiment selects an LLM team. Model names in
the experiment code are stable project aliases:

| Alias | Default Ollama tag | Environment override |
| --- | --- | --- |
| `small_reasoner` | `qwen2.5:3b` | `MOSAIC_MODEL_SMALL` |
| `small_reasoner_alt` | `llama3.2:3b` | `MOSAIC_MODEL_SMALL_ALT` |
| `large_reasoner` | `qwen2.5:7b` | `MOSAIC_MODEL_LARGE` |

Pull only the model you need, then run for example:

```bash
ollama pull qwen2.5:3b
.venv/bin/python -m experiments.run_llm --seeds 2 --teams mixed
```

Set `MOSAIC_OLLAMA_URL` when Ollama is reachable at a non-default address. A
response cache is created in `results/llm_cache/`; it is intentionally local and
is not part of the source distribution.

## Project layout

```text
src/mosaic_comm/   simulator, world model, beliefs, channels, schemes, LLM client
experiments/       paper campaigns, analysis, and plotting
scripts/           focused sample and cache utilities
tests/             unit and regression tests
docs/              architecture and reproducibility notes
```

The simulator keeps the research scheme identifiers (`gosc`, `sem`, `genie`, and
the related baselines) stable so existing experiment results remain comparable.
New code should depend on `mosaic_comm.Config` and `mosaic_comm.run_episode`, and
put new experiment-specific orchestration under `experiments/`.

## License and citation

MIT. See [LICENSE](LICENSE). If you use the research implementation, cite the
paper listed in the original repository and describe any changes to the simulator
configuration or model backend.

