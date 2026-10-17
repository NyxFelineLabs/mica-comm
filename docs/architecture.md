# Architecture

MOSAIC-Comm has one simulation path and a thin experiment layer.

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
- `simulator.py`: one mission's sense, plan, transmit, fuse, broadcast, and move loop.
- `realistic.py`: packet overhead, imperfect valuation, and shared uplink extensions.

`run_episode` is the stable programmatic entry point. It accepts a `Config`, a
scheme name, and a seed, and returns JSON-serializable mission metrics.

## Extension points

1. Add a field to `Config` for a new controlled parameter.
2. Add a scheme or value rule in `schemes.py` while preserving existing names.
3. Add a focused experiment runner under `experiments/`.
4. Add tests for deterministic behavior and one regression metric.

Keep model-specific code behind `llm_agent.py`; experiments should select aliases
instead of embedding provider tags.

