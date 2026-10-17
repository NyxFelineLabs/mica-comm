# Architecture

MOSAIC-Comm has one simulation path and a thin experiment layer. It implements
MICA (Multiagent Information Coordination Architecture), which coordinates
message selection, task-value estimation, and transmission-rate allocation.

```text
Config
  -> Simulation
       -> World and SensorModel
       -> Agent / LLMAgent planners
       -> Channel and message encoding
       -> Scheme scheduler and value model
       -> edge fusion, broadcast, and movement
  -> episode metrics
```

## Core modules

- `config.py`: immutable simulation parameters and `Config.with_(...)` overrides.
- `environment.py`: hidden victims, sensing, deadlines, and rescue state.
- `belief.py`: log odds, observations, and local/common belief updates.
- `agent.py` and `llm_agent.py`: classical and Ollama-backed intention planners.
- `channel.py` and `messages.py`: fading link, packet errors, and bit accounting.
- `schemes.py`: semantic and conventional communication policies.
- `joint.py`: joint evidence/intent valuation through `JointMicaScheduler`.
- `simulator.py`: one mission's sense, plan, transmit, fuse, broadcast, and move loop.
- `realistic.py`: packet overhead, imperfect valuation, and shared uplink extensions.

`run_episode` is the stable programmatic entry point. It accepts a `Config`, a
scheme name, and a seed, and returns JSON-serializable mission metrics.

The default policy ID is `mica`, implemented by `MicaScheduler`.
`JointMicaScheduler` extends it with joint valuation, while
`ResourceAwareMicaScheduler` adds packet overhead, imperfect values, and shared
budgets. Policy factories are registered in `SCHEMES` and `REALISTIC_SCHEMES`.

Experiment output paths are centralized in `mosaic_comm.paths`. `results/` and
`figures/` can be redirected with `MOSAIC_RESULTS_DIR` and `MOSAIC_FIGURES_DIR`;
the LLM cache uses `MOSAIC_CACHE_DIR`.

## Extension points

1. Add a field to `Config` for a new controlled parameter.
2. Add a policy or value rule in `schemes.py` and register its ID.
3. Add a focused experiment runner under `experiments/`.
4. Add tests for deterministic behavior and one regression metric.

Keep model-specific code behind `llm_agent.py`; experiments should select aliases
instead of embedding provider tags.

Keep policy IDs consistent across runners, result keys, and plot labels. Document
identifier changes and data migration requirements in [Experiment workflow](experiments.md).

