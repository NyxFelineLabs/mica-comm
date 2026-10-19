<div align="center">

# MICA

**Multiagent Information Coordination Architecture**

Task-oriented semantic communication for heterogeneous agent teams

[![CI](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml/badge.svg)](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

**English** · [简体中文](README.zh-CN.md)

[Quick start](#quick-start) · [Structure](#structure) · [Results](#results) · [Figure catalog](reports/current/README.md)

</div>

---

## Overview

MICA studies **which semantics to transmit, when communication is useful, and how to allocate limited channel resources** in grid-based search and rescue. Agents use local observations to find hidden targets and exchange confirmations, evidence, and search intentions. Communication changes subsequent search decisions.

The executable missions use a task-value scheduler: predict the effect of a message on teammates' search utility, then account for delivery probability and symbol cost when selecting messages and transmission rates. Agents support classical planners and local LLMs through Ollama. The on-demand evidence components in `demand/` have protocol tests but are not integrated into a full mission loop.

## Quick start

Use your existing Python environment in WSL. Install this project in editable mode once:

```bash
python -m pip install -e ".[dev]"
mica-mission --scheme mica --seed 9000
python -m pytest -q
```

Default missions need no LLM server. For online model experiments, point the endpoint at Windows Ollama; replace localhost with the Windows host address if needed from WSL.

```bash
python -m experiments.run_team_benchmark --help
python -m experiments.run_team_benchmark --url http://localhost:11434 \
  --seeds 12 --output results/team_new
```

Models: `qwen3:8b`, `llama3.1:8b`, and `gemma3:12b`. Each mission combines three agents using one selected model with three classical planners; these runs do not mix all three models in one team.

## Structure

```text
mica-comm/
├── src/mica_comm/
│   ├── core/              # Configuration, paths, source fingerprints
│   ├── world/             # World, beliefs, rescue task
│   ├── agents/            # Planners, LLM client, behavior prediction
│   ├── communication/     # Messages, channel, scheduling, joint selection
│   ├── simulation/        # Mission loop, broadcasts, resource accounting
│   ├── demand/            # On-demand protocol; not mission-integrated
│   ├── evaluation/        # Cohort and configuration validation
│   └── visualization/     # Style, fonts, bilingual labels
├── experiments/           # Runners and analysis
├── scripts/               # Import and cache tools
├── tests/                 # Behavior, protocol, and integrity tests
├── reports/current/       # Outcome snapshots, statistics, figure index
├── figures/current/       # Chinese/English PDF, SVG, PNG figures
└── results/               # Local logs/caches; Git-ignored
```

The `src` layout keeps one `mica_comm` namespace with focused subpackages. Reusable mission and communication logic belongs in the package; experiment runners handle parameters and orchestration. Public API:

```python
from mica_comm import Config, run_episode

config = Config().with_(grid=32, n_agents=6, symbols_per_slot=100)
result = run_episode(config, "mica", seed=9000)
```

## Results

### Classical planner teams

On 2026-10-19, **1,272 missions** ran in WSL: 106 configuration cells with the same 12 seeds per cell (9000–9011). Defaults: a $32\\times32$ grid, six agents, eight hidden targets, 100 symbols per agent per slot, 5 dB reference SNR, and a 400-slot horizon.

| Communication policy | Time / slots | Uplink symbols | Total symbols | Completion |
| --- | ---: | ---: | ---: | ---: |
| Timed state sharing (SYNC) | 82.25 | 43,407.83 | 49,734.17 | 100% |
| Task-value scheduling (MICA) | 65.25 | 11,509.25 | 14,658.08 | 100% |
| Instant sharing (IDEAL) | 68.17 | — | — | 100% |

IDEAL bypasses uplink delivery constraints; its zero uplink accounting does not mean zero physical cost. Total symbols include uplink data, requests, broadcasts, feedback, and grants. See [mission metrics](reports/current/metrics.csv) and the [configuration manifest](reports/current/manifest.json).

![Mission time and uplink cost](reports/current/previews/en_standard.png)

### Heterogeneous LLM teams

These 108 missions generated online responses on 2026-10-18. The refactor replayed our own response caches and verified every mission metric with no new inference requests. Each model-policy cell has 12 seeds (8000–8011); all missions completed without backend fallback.

| Model | SYNC time | MICA time | IDEAL time | SYNC uplink symbols | MICA uplink symbols |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 8B | 80.58 | 89.83 | 73.92 | 41,115.25 | 15,687.00 |
| Llama 3.1 8B | 93.83 | 90.75 | 88.58 | 48,761.83 | 15,094.08 |
| Gemma 3 12B | 120.92 | 85.00 | 62.25 | 64,759.17 | 13,837.67 |

Time means **simulation slots**, not inference seconds. Gemma has 12B parameters; the other models have 8B. These outcomes do not establish parameter-scale or inference-compute efficiency. See [LLM statistics](reports/current/llm/summary.json).

![Language-model mission outcomes](reports/current/previews/en_llm.png)

## Figures and reproduction

The [bilingual catalog of 18 figure topics](reports/current/README.md) covers time/cost, progress, team size, budgets, SNR, broadcast reliability, shared resources, finite blocklength, rescue deadlines, tradeoffs, components, trajectories, model differences, and valuation noise. Chinese filenames describe their contents, for example `15_多智能体搜索轨迹.pdf`.

The repository publishes validated result snapshots and final vector figures. The plotting implementation is kept private. To rerun the classical-planner campaign for a new study:

```bash
python -m experiments.run_current --seeds 12 --workers 6 --output results/current_new
```

Published bands and error bars are exploratory mission-seed bootstrap 95% intervals without multiplicity adjustment. Unfinished missions retain the horizon time. Figure 13 shows mean budget tradeoffs without claiming global Pareto optimality; the trajectory example uses the first seed.

Earlier local figures are preserved in `results/figure_archive_20261019/`.
