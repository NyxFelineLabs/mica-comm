# Softmax calibration experiment results

Run on 2026-10-17 in WSL, starting from source revision `a45f36d` with the
receiver-calibration changes. All missions use classical planners. No Ollama
models, author response caches, or live LLM calls enter these experiments.

## Protocol

Training uses default-scenario seeds `1000..1015`, recording one target decision
per agent every five slots. Receiver-specific parameters minimize supervised
target negative log-likelihood. All parameters are frozen before evaluation.
The four evaluation variants change only the softmax teammate predictor.
See [Behavior calibration](behavior_calibration.md) for the full method.

The initial evaluation uses seeds `3000..3029` in each of four scenarios, with
four variants per seed: 480 mission runs. All variants use the same communication
price `1e-5` and the same per-scenario configured bandwidth. Parameter selection
uses no evaluation mission outcomes. The evaluation is exploratory.

## Frozen parameters

| Variant | Temperatures for agents 0..5 | Persistence bonuses for agents 0..5 |
| --- | --- | --- |
| Baseline | 0.1, 0.1, 0.1, 0.1, 0.1, 0.1 | 0, 0, 0, 0, 0, 0 |
| Temperature only | 0.1, 0.1, 0.1, 0.1, 0.1, 0.1 | 0, 0, 0, 0, 0, 0 |
| Persistence only | 0.1, 0.1, 0.1, 0.1, 0.1, 0.1 | 4, 2, 4, 4, 4, 0 |
| Combined | 0.2, 0.2, 0.2, 0.2, 0.1, 0.1 | 4, 4, 4, 4, 4, 0 |

Temperature-only training selects the unchanged baseline, so that ablation
produces identical mission metrics. The final agent's zero persistence is also
consistent with its lower planning priority and the available intent messages;
this experiment does not identify model-specific LLM behavior.

## Prediction accuracy

On held-out default-scenario baseline trajectories, decision-weighted negative
log-likelihood is:

| Variant | Target NLL, lower is better |
| --- | ---: |
| Baseline | 4.7357 |
| Temperature only | 4.7357 |
| Persistence only | 4.1995 |
| Combined | 4.0125 |

The combined predictor reduces NLL by 15.3%. This measures target prediction,
not the causal effect of receiving a message or mission quality.

## Initial mission evaluation

Mean completion slots and uplink symbols; all 480 runs complete successfully.
Percent symbol changes compare the combined variant with the baseline.

| Scenario | Baseline slots | Persistence slots | Combined slots | Baseline symbols | Combined symbols | Symbol change |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 72.30 | 74.17 | 86.27 | 12,020.4 | 10,666.6 | -11.3% |
| Bandwidth 50 | 77.77 | 83.90 | 95.47 | 7,239.6 | 6,686.0 | -7.6% |
| Clustered survivors | 51.10 | 56.17 | 47.63 | 9,399.6 | 7,783.4 | -17.2% |
| Reference SNR -5 dB | 105.07 | 109.60 | 95.27 | 12,288.6 | 10,249.1 | -16.6% |

Paired seed-bootstrap intervals below give combined minus baseline. Negative
differences favor the combined model. These 95% intervals are unadjusted for
the multiple exploratory comparisons.

| Scenario | Slot difference, 95% interval | Symbol difference, 95% interval |
| --- | --- | --- |
| Default | +13.97 [-7.93, +33.83] | -1,353.8 [-2,998.5, +177.5] |
| Bandwidth 50 | +17.70 [-3.83, +43.73] | -553.6 [-1,501.5, +360.6] |
| Clustered survivors | -3.47 [-11.73, +4.13] | -1,616.1 [-2,853.4, -364.5] |
| Reference SNR -5 dB | -9.80 [-30.20, +8.33] | -2,039.5 [-3,282.4, -774.4] |

There is no established completion-time improvement in any initial scenario.
The clustered and weak-signal scenarios have promising communication savings;
default and low-bandwidth runs show a worse mean completion time. Lower target
prediction loss alone is insufficient to establish better collaboration.

## Independent clustered-scenario confirmation

After observing the initial clustered-scenario communication savings, a second
evaluation uses 100 new seeds, `4000..4099`, in that scenario only. This scenario
was selected after the exploratory stage. The parameter grid and fitted
parameters are unchanged; the two saved `calibration.json` files are identical.
All four variants are rerun: 400 additional mission runs, or 880 comparison runs
across both stages, excluding training and prediction diagnostics.

| Variant | Mean completion slots | Mean uplink symbols | Completion rate |
| --- | ---: | ---: | ---: |
| Baseline | 57.41 | 10,248.80 | 100% |
| Temperature only | 57.41 | 10,248.80 | 100% |
| Persistence only | 54.26 | 9,270.09 | 100% |
| Combined | 55.76 | 8,622.37 | 100% |

The combined model saves **15.9%** of uplink symbols. The paired mean symbol
difference is -1,626.43 with a 95% bootstrap interval of [-2,455.97, -807.12].
The mean slot difference is -1.65 with interval [-9.24, +5.57]. Communication
savings replicate, but a completion-time gain is not established. The unchanged
observed completion rate also does not prove statistical non-inferiority for
completion time or establish generalization to other scenarios.

Persistence alone saves 9.5% of symbols, with difference -978.71 and interval
[-1,809.44, -181.30]. Its slot difference, -3.15 [-10.40, +4.34], also includes
zero. The combined model has a lower mean symbol count than persistence alone;
the intervals above compare each variant with baseline, not with each other.

Prediction diagnostics for the second stage again use **default-scenario**
baseline trajectories, now on seeds `4000..4099`, rather than the clustered
mission trajectories. NLL is 4.8073 for baseline and 4.0693 for the combined
model. This repeats the likelihood improvement without establishing that it
causes the measured communication saving.

## Interpretation

The tested change provides a repeatable communication saving in clustered
search. It does not provide a general completion-time improvement: the initial
default and bandwidth-limited experiments have worse mean completion times.
Temperature-only fitting does not improve the baseline, and a likelihood gain
must not be reported as a task-performance gain.

A plausible explanation is that modeling target persistence reduces the
estimated effect of some announcements and evidence updates, suppressing
transmissions. Whether those suppressed messages are unnecessary or important
depends on the scenario. This is a hypothesis; the experiment has not measured
counterfactual decision-response accuracy or tested equal actual-symbol budgets.

## Reproduce

```bash
python -m experiments.run_behavior_calibration --train-seeds 16 --eval-seeds 30 --workers 4
python -m experiments.run_behavior_calibration --train-seeds 16 --eval-seeds 100 --eval-start 4000 --scenarios clustered --workers 4 --output results/behavior_calibration_cluster_confirmation
```

Raw runs, calibration, and summaries are local in
`results/behavior_calibration/` and `results/behavior_calibration_cluster_confirmation/`.
They are ignored by Git. The script preserves
per-seed results, checks training/evaluation seed separation, and supports
resuming mission jobs. Use a fresh output directory after code or grid changes.

The new calibration remains opt-in; default MICA is unchanged. Interpretation
must distinguish actual symbol use from configured bandwidth, and simulated
completion slots from execution latency. These results do not demonstrate an
advantage for heterogeneous LLM teams or at equal actual communication cost.

For a separate live-model evaluation, see
[LLM team calibration results](llm_behavior_calibration_results.md). Its observed
communication savings come with worse mean completion slots in all four
model/scenario comparisons.
