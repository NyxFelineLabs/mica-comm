# Experiment workflow

The deterministic simulator does not need an LLM or a network connection.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m mosaic_comm.simulator --scheme mica --seed 0
python -m experiments.run_all --only default --seeds 2
```

## Experiment groups

| Module | Purpose |
| --- | --- |
| `experiments.run_all` | Baselines and sweeps over SNR, bandwidth, team size, and price |
| `experiments.run_robustness` | Ablations, value rules, downlink loss, and coding effects |
| `experiments.run_realistic` | Packet overhead, shared uplink budgets, and value estimation noise |
| `experiments.run_joint` | Independent and joint evidence/intent valuation |
| `experiments.run_belief_divergence` | Belief-based valuation in larger teams and clustered scenes |
| `experiments.run_llm` | Planner-only and heterogeneous LLM teams |
| `experiments.run_llm_extended` | Additional models, teams, and seeds |
| `experiments.analyze_scheduler` | Scheduler optimality gap and value additivity |
| `experiments.analyze_theory` | Budget thresholds, duality bounds, and rate efficiency |
| `experiments.diagnose_value` | Task-value estimates and decision effects |
| `experiments.validate_outcomes` | Select operating points and validate on held-out seeds |

Inspect each runner's `--help` before a long run. Start with a small seed count,
then increase it for statistical comparisons. `experiments.plot` handles baseline
outputs; `experiments.plot_robustness` and `experiments.plot_realistic` consume
their respective experiment groups. Run the required groups before those plots.

For baseline figures, generate every baseline sweep first:

```bash
python -m experiments.run_all --seeds 100
python -m experiments.plot
```

## Fair comparisons

Keep the same seed set and `Config` values for every policy. The simulator uses
common random numbers: a seed fixes the world, launch positions, sensing draws,
and channel draws shared by policies in that mission.

The default seed-0 `mica` mission completes in 122 slots and uses 13,304 uplink
symbols. Use these values as a software regression check.

Report completion rate, completion slots, uplink symbols, and rescue outcomes as
appropriate to the task. For LLM runs, also report model tags, fallback counts,
cache hits, and actual inference time. Simulated slots and elapsed inference time
measure different things; cached replay does not measure online inference speed.

## Output conventions

Outputs and figures are local, ignored by Git, and can be redirected with
`MOSAIC_RESULTS_DIR` and `MOSAIC_FIGURES_DIR`. Robustness data files use the prefix
`robustness_`; their aggregate summary is `summary_robustness.json`.

The naming update changes policy IDs, class imports, experiment module names,
and several result keys. Use the current IDs in the README and regenerate data
before running analysis. Older output files are not migrated automatically.
Keep previous runs in a separate directory and give new campaigns their own
output directory, for example:

```bash
export MOSAIC_RESULTS_DIR="$PWD/results/mica-evaluation"
export MOSAIC_FIGURES_DIR="$PWD/figures/mica-evaluation"
python -m experiments.run_robustness --only ablation --seeds 2
```
