# MOSAIC-Comm

MOSAIC-Comm is an experiment platform for communication and collaboration in
heterogeneous agent teams. Search-and-rescue missions combine local sensing,
shared beliefs, wireless links, and optional LLM planners.

Use it to develop communication policies, compare model backends, and measure
task outcomes under limited bandwidth. The package includes deterministic
simulation, baseline policies, ablations, and analysis tools.

The communication framework is **MICA** (**M**ultiagent **I**nformation
**C**oordination **A**rchitecture). MOSAIC-Comm is the software project; MICA is
the framework name used in publications, documentation, and figure labels. Its
command-line policy ID is `mica`.

## Quick start

Python 3.9 or newer is supported.

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest -q
```

Run one deterministic mission:

```bash
.venv/bin/python -m mosaic_comm.simulator --scheme mica --seed 0
```

On Windows, use `.venv\Scripts\python.exe` in the same commands. The package
is installed in editable mode, so changes under `src/mosaic_comm` are immediately
available to the experiment scripts.

## Communication policies

| Policy ID | Behavior |
| --- | --- |
| `mica` | Select messages and transmission rates using estimated task value |
| `mica_tv` | Score messages by their effect on the shared belief |
| `mica_bits` | Score messages by payload size |
| `mica_aoi` | Score messages by information freshness |
| `mica_joint` | Value evidence and intent together |
| `sem`, `sem_agg` | Periodic semantic reporting, with optional aggregation |
| `sem_ra`, `sem_raf`, `sem_ras` | Rate-aware periodic reporting and filtering variants |
| `raw`, `nl`, `report` | Raw-data, text-message, and confirmation-only baselines |
| `genie` | Ideal delivery reference |

`mica_nofilter`, `mica_novoi`, `mica_nouep`, and `mica_joint_nb`
disable source filtering, task valuation, importance-aware rate selection, and
joint bundling, respectively. List all available IDs with
`python -m mosaic_comm.simulator --help`.

## Experiments

All experiment commands write local output under `results/` and generated plots
under `figures/`; both are ignored by Git.

The locations can be redirected without changing code, which is useful for WSL
mounts and CI workers:

```bash
export MOSAIC_RESULTS_DIR=/tmp/mosaic-results
export MOSAIC_FIGURES_DIR=/tmp/mosaic-figures
```

```bash
.venv/bin/python -m experiments.run_all --only default --seeds 2
.venv/bin/python -m experiments.run_robustness --only ablation --seeds 2
```

See [Experiment workflow](docs/experiments.md) for sweeps, validation, and output
conventions. Increase the seed count after verifying a small run. Compare
policies using identical seed sets and configurations.

To evaluate receiver-specific softmax calibration against the unchanged default:

```bash
.venv/bin/python -m experiments.run_behavior_calibration --train-seeds 16 --eval-seeds 30 --workers 4
```

The runner fits parameters on separate training seeds, freezes them, and evaluates
temperature-only, persistence-only, and combined variants. See
[Behavior calibration](docs/behavior_calibration.md) for the protocol and limitations.

To test the same softmax change with installed Qwen3 and Llama 3.1 models:

```bash
.venv/bin/python -m experiments.run_llm_calibration
```

See [LLM behavior calibration](docs/llm_behavior_calibration.md) for the held-out
protocol, inference settings, and Windows Ollama access from WSL.
The [measured LLM results](docs/llm_behavior_calibration_results.md) show lower
communication use but worse mean completion slots in all four comparisons;
calibration remains opt-in.

## Optional Ollama backend

LLM agents call a locally managed Ollama server. Assign installed model tags to
project aliases using environment variables; the aliases identify experiment
roles and do not imply a measured capability ranking. For example:

```bash
export MOSAIC_MODEL_SMALL=llama3.1:8b
.venv/bin/python -m experiments.run_llm --seeds 2 --teams mixed
```

Use a tag already installed in your Ollama server. Set `MOSAIC_OLLAMA_URL` when
the server uses a non-default address. Responses are cached locally under
`results/llm_cache/`, which can be redirected with `MOSAIC_CACHE_DIR`.
See [Model backends](docs/model_backends.md) for all aliases and cache behavior.

## Project layout

```text
src/mosaic_comm/   simulator, world model, beliefs, channels, schemes, LLM client
experiments/       experiment runners, analysis, and plotting
scripts/           focused sample and cache utilities
tests/             unit and regression tests
docs/              architecture, experiment workflow, and backend configuration
.github/           continuous integration checks
```

Use `mosaic_comm.Config` and `mosaic_comm.run_episode` as the programmatic entry
points. Add reusable policies under `src/mosaic_comm/` and experiment orchestration
under `experiments/`. See [Architecture](docs/architecture.md) and
[Contributing](CONTRIBUTING.md) for extension and development conventions.

## License

MIT. See [LICENSE](LICENSE) and [NOTICE](NOTICE.md) for copyright and source
attribution. Record the code revision, configuration, model tags, and seed set
when publishing experimental results.

