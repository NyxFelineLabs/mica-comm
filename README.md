<div align="center">

# MICA

**Multiagent Information Coordination Architecture**

Task-oriented semantic communication for heterogeneous agent teams

[![CI](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml/badge.svg)](https://github.com/NyxFelineLabs/mica-comm/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?logo=python&logoColor=white)](pyproject.toml)

**English** · [简体中文](README.zh-CN.md)

[Quick start](#quick-start) · [Structure](#structure) · [Definitions](#definitions) · [Results](#results) · [Figure catalog](reports/current/README.md)

</div>

---

## Overview

MICA studies **which semantics to transmit, when communication is useful, and how to allocate limited channel resources** in grid-based search and rescue. Agents use local observations to find hidden targets and exchange confirmations, evidence, and search intentions. Communication changes subsequent search decisions.

The executable missions use a task-value scheduler: predict the effect of a message on teammates' search utility, then account for delivery probability and symbol cost when selecting messages and transmission rates. Agents support classical planners and local LLMs through Ollama. The on-demand evidence components in `demand/` have protocol tests but are not integrated into a full mission loop; results below use the executable mission simulator.

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

Models: `qwen3:8b`, `llama3.1:8b`, `gemma3:12b`. Each mission combines three agents using one selected model with three classical planners; these runs do not mix all three models in one team.

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
├── experiments/           # Runners, analysis, plotting
├── scripts/               # Import and cache tools
├── tests/                 # Behavior, protocol, and integrity tests
├── reports/current/       # Outcome snapshots, statistics, figure index
├── figures/current/       # Chinese/English PDF, SVG, PNG
└── results/               # Local logs/caches; Git-ignored
```

The `src` layout keeps one `mica_comm` namespace with focused subpackages. Reusable logic belongs in the package; experiment runners handle parameters and orchestration. Public API:

```python
from mica_comm import Config, run_episode

config = Config().with_(grid=32, n_agents=6, symbols_per_slot=100)
result = run_episode(config, "mica", seed=9000)
```

## Definitions

These expressions describe the executable mission simulator. The default teammate model uses one temperature; receiver-specific temperatures and intention persistence are optional.

| Component | Core expression | Meaning |
| --- | --- | --- |
| Grid and team | $\mathcal X=\{0,\ldots,G-1\}^2$, $\lvert\mathcal A\rvert=A$, $N_{\mathrm v}$ | Grid cells, agent set and count, and number of hidden survivors. $x_a(t)$ and $y_a(t)$ are agent $a$'s position and target. |
| Sensor evidence | $\kappa_+=\ln\frac{p_{\mathrm{hit}}}{p_{\mathrm{fa}}}$, $\kappa_-=\ln\frac{1-p_{\mathrm{hit}}}{1-p_{\mathrm{fa}}}$ | Log-likelihood increments for a detection and a non-detection. |
| Belief | $\ell_{a,t}(z)=\ell_t^{\mathrm{sh}}(z)+\epsilon_{a,t}(z)$, $P_{a,t}(z)=\operatorname{sigm}(\ell_{a,t}(z))$ | Shared log-odds plus agent-local pending evidence, converted to occupancy probability. |
| Search planning | $B_{a,t}(z)=\sum_{q\in F_{r_{\mathrm s}}(z)}P_{a,t}(q)$; $\Psi_{a,t}(z)=\frac{B_{a,t}(z)}{1+\alpha_d\lVert z-x_a(t)\rVert_1}\prod_{q\in\mathcal Y_{a,t}}\left(1-e^{-\lVert z-q\rVert_2^2/(2\omega^2)}\right)$; $y_a(t)\in\arg\max_z\Psi_{a,t}(z)$ | Expected survivor mass, discounted by travel and overlap with teammates, determines the next search target. |
| Teammate prediction | $\varpi_a(z\mid\mathcal K_t)=\operatorname{softmax}_z\!\left(\frac{\Psi_a(z;\mathcal K_t)}{\tau_a^{\mathrm{tom}}\max_w\Psi_a(w;\mathcal K_t)}\right)$ | Normalized-score softmax predicts teammates' targets; $\tau_a^{\mathrm{tom}}>0$ controls its concentration. |
| Information value | $\mathcal I(m)=\sum_{a\ne s}\left(\mathbb E_{z\sim\varpi_a(\cdot\mid\mathcal K_t\oplus m)}U_a(z;\mathcal B_s)-\mathbb E_{z\sim\varpi_a(\cdot\mid\mathcal K_t)}U_a(z;\mathcal B_s)\right)$ | Expected change in teammates' search utility after sender $s$ shares message $m$. |
| Path loss and link success | $\Gamma_a(t)=\Gamma_0\left(\frac{d_0}{\max\{d_a(t),d_{\min}\}}\right)^{\alpha_{\mathrm{pl}}}$; $\Pi(\nu;\Gamma)=e^{-(2^\nu-1)/\Gamma}$ | Mean SNR under the configured path-loss model and default Rayleigh-outage packet success probability. |
| Option value | $u_{mq}=\left\lceil\frac{b_{mq}+h_0}{\nu_{mq}}\right\rceil$; $F_{mq}(\Lambda)=g_{mq}\Pi(\nu_{mq};\Gamma)-\Lambda u_{mq}$ | Channel uses and task value after accounting for packet success and communication cost. |
| Slot scheduler | $\max_{x_{mq}\in\{0,1\}}\sum_{m,q}x_{mq}F_{mq}(\zeta)$, with $\sum_qx_{mq}\le1$ and $\sum_{m,q}x_{mq}u_{mq}\le C$ | Select at most one option per message group under the active capacity. The dual rule evaluates options at $\Lambda=\zeta+\Delta_C$. |
| Mission objective | $\min_\pi\mathbb E[\mathcal L_{\mathrm{task}}+\zeta U_{\mathrm{tx}}]$ | Trade off task loss and uplink use. For search, $\mathcal L_{\mathrm{task}}=\tau_{\mathrm{end}}$; rescue loss counts survivors missed by their deadlines. |
| Rescue outcome | $\rho_{\mathrm{save}}=\frac{1}{N_{\mathrm v}}\sum_{z\in\mathcal S}\mathbf1\{t_z^{\mathrm{done}}<d_z\}$ | Saved fraction; $t_z^{\mathrm{done}}$ is the actual service completion slot, or $+\infty$ if unfinished. |

Allocation uses multiplier search and greedy residual filling, without a global integer or mission optimality guarantee. Classical planners also use target hysteresis; LLMs select among supplied candidates. Finite blocklength uses a separate error model.

## Results

### Classical planner teams: fresh execution

On 2026-10-19, **1,272 missions** ran in WSL: 106 configuration cells with the same 12 seeds per cell (9000–9011). Defaults: $32\times32$ grid, six agents, eight hidden targets, 100 symbols per agent per slot, 5 dB reference SNR, and a 400-slot horizon.

| Communication policy | Time / slots | Uplink symbols | Total symbols | Completion |
| --- | ---: | ---: | ---: | ---: |
| Timed state sharing (SYNC) | 82.25 | 43,407.83 | 49,734.17 | 100% |
| Task-value scheduling (MICA) | 65.25 | 11,509.25 | 14,658.08 | 100% |
| Instant sharing (IDEAL) | 68.17 | — | — | 100% |

Values are default-setting means. IDEAL bypasses uplink delivery constraints; its zero uplink accounting does not mean zero physical cost. Total symbols include uplink data, requests, broadcasts, feedback, and grants. See [mission metrics](reports/current/metrics.csv) and [configuration/source manifest](reports/current/manifest.json).

![Mission time and uplink cost](reports/current/previews/en_standard.png)

### Heterogeneous LLM teams: verified replay

These 108 missions generated online responses on 2026-10-18. This refactor replayed our own caches and verified every mission metric against measured records, with no new inference requests. Each model-policy cell has 12 seeds (8000–8011); all missions completed without backend fallback.

| Model | SYNC time | MICA time | IDEAL time | SYNC uplink symbols | MICA uplink symbols |
| --- | ---: | ---: | ---: | ---: | ---: |
| Qwen3 8B | 80.58 | 89.83 | 73.92 | 41,115.25 | 15,687.00 |
| Llama 3.1 8B | 93.83 | 90.75 | 88.58 | 48,761.83 | 15,094.08 |
| Gemma 3 12B | 120.92 | 85.00 | 62.25 | 64,759.17 | 13,837.67 |

Time means **simulation slots**, not inference seconds. Gemma has 12B parameters; the other models have 8B. These outcomes do not establish parameter-scale or inference-compute efficiency. Model behavior also changes across communication policies. See [intervals and paired contrasts](reports/current/llm/summary.json).

![Language-model mission outcomes](reports/current/previews/en_llm.png)

## Figures and reproduction

The [bilingual catalog of 18 figure topics](reports/current/README.md) covers time/cost, progress, team size, budgets, SNR, broadcasts, shared resources, finite blocklength, rescue deadlines, tradeoffs, components, trajectories, models, and valuation noise. Chinese filenames describe their contents, e.g. `15_多智能体搜索轨迹.pdf`.

Rebuild figures directly from published outcome snapshots:

```bash
python -m experiments.plot_current \
  --input reports/current --llm-input reports/current/llm \
  --language both
```

Run the full classical-planner campaign again, then plot:

```bash
python -m experiments.run_current --seeds 12 --workers 6 --output results/current_new
python -m experiments.plot_current \
  --input results/current_new --llm-input reports/current/llm \
  --language both
```

The plotting entry validates seeds, configurations, and cohort completeness. Bands/error bars show exploratory mission-seed bootstrap 95% intervals without multiplicity adjustment. Unfinished missions retain the horizon time. Figure 13 shows mean budget tradeoffs without claiming global Pareto optimality; trajectories use the first seed.

PDF/SVG files are tracked; local exports include 600 dpi PNGs and layout audits. README previews are compact. Chinese rendering supports Windows Microsoft YaHei from WSL or installed Noto Sans CJK SC. Earlier local figures are preserved in `results/figure_archive_20261019/`.

## Development checks

```bash
black --check src tests experiments scripts
ruff check src tests experiments scripts
python -m pytest -q
```

Configuration belongs in `core/config.py`, message/link logic in `communication/`, and mission stages in `simulation/`. Use a fresh output directory after changing computation: resumed runs check source fingerprints and experimental design.
