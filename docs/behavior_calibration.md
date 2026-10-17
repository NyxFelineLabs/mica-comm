# Receiver behavior calibration

See [Experiment results](behavior_calibration_results.md) for measured outcomes.

This experiment changes only the softmax teammate predictor in `voi.py`.
The default configuration retains the original calculation. Planners, message
encoding, source filtering, transmission selection, channel draws, and mission
rules are shared between baseline and calibrated runs.

## Predictor

For teammate `j`, let `s_j(c)` be the existing score for cell `c`, combining
shared survivor mass, distance, and avoidance of teammates. The calibrated
prediction is proportional to:

```text
exp(s_j(c) / (temperature_j * max(s_j))
    + persistence_j * indicator(c == publicly_announced_target_j))
```

The persistence term is absent when the teammate has no announced target.
The ordinary baseline uses temperature `0.1` and persistence `0` for everyone.
Set `Config.tom_temperatures` and `Config.tom_persistence` to tuples containing
one parameter per agent to enable calibration. Empty tuples preserve defaults.

Only public intentions enter the persistence term. Private teammate beliefs and
private current targets are not predictor inputs under the default, non-oracle
configuration. The existing sender-local belief still evaluates task utility,
as in the baseline value-of-information calculation.

## Training and evaluation

```bash
python -m experiments.run_behavior_calibration --train-seeds 16 --eval-seeds 30 --workers 4
```

Default training seeds are `1000..1015`. Evaluation uses `3000..3029`.
Training missions use the baseline policy in the default search scenario.
Every five slots, the runner records shared predictor features and the actual
post-planning target of each agent. Actual targets are supervised labels from
simulation instrumentation, including targets that have not been announced;
they are never exposed to the runtime predictor.

Grid search minimizes target negative log-likelihood separately for each agent:

- Temperature: `0.02, 0.04, 0.07, 0.1, 0.2, 0.4, 0.8`.
- Persistence logit bonus: `0, 1, 2, 4, 8`.
- Variants: unchanged baseline, temperature only, persistence only, and combined.

Parameters are frozen before evaluation. Prediction likelihood is evaluated on
held-out baseline trajectories, providing the same labeled states for every
predictor. Mission outcomes are evaluated by rerunning each variant with the
same world, sensing, planning, and channel seed streams.

The four scenarios are default search, 50-symbol bandwidth, clustered survivors,
and reference SNR of -5 dB. All variants retain the same configured bandwidth
and communication price; actual communication use can differ.

## Outputs and interpretation

Results are local under `results/behavior_calibration/`:

- `training.json`: accumulated prediction losses and sample counts per training seed.
- `calibration.json`: frozen parameters for each variant and agent.
- `prediction_validation.json`: held-out likelihoods and per-seed loss sums.
- `missions.jsonl`: individual mission metrics, appended as jobs finish.
- `summary.json`: averages and paired bootstrap intervals for differences.

Negative slot and symbol differences favor the calibrated variant. Intervals
resample mission seeds as pairs; they are exploratory, unadjusted 95% bootstrap
intervals across multiple variants and scenarios. Prediction loss averages are
weighted by sampled target decisions. Held-out prediction trajectories use the
baseline policy and may differ from states visited by calibrated policies.

These runs use classical planners, not live LLMs. An improvement on these runs
does not establish an improvement with heterogeneous LLMs. Agent indices also
encode planning priority, so per-agent parameters may learn priority effects.
The training procedure assumes access to instrumented target labels; deployment
with only sparse public announcements would require a separate data protocol.

Mission completion slots are simulated steps. Report them separately from wall
time and online LLM latency. A faster mission accompanied by increased symbol
use is a tradeoff, not an improvement at equal actual communication cost.

Use a fresh `--output` directory after changing the parameter grid, model code,
or training settings. Files from different experiments must not be mixed.
