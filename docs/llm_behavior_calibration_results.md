# LLM team calibration results

Measured on 2026-10-17 using WSL Ubuntu 22.04 simulation and Windows Ollama
0.33.3 on an RTX 3090 with 24 GB VRAM. Both installed models use Q4_K_M
quantization. Source starts at revision `0996630` with the new LLM experiment
runner. Model digests, source hash, configuration, and frozen calibration are
recorded in each local `manifest.json` and `calibration.json`.

This evaluates the effect of teammate softmax calibration on LLM teams. The
LLM weights are not trained. Each model runs in a separate team with three LLM
agents (0, 2, 4) and three classical planners. Both receiver types are calibrated.
See the [full protocol](llm_behavior_calibration.md) for settings and limitations.
Only baseline and combined calibration are evaluated here; these LLM runs do
not isolate the effects of temperature and persistence from each other.

**Result:** all four comparisons save mean uplink symbols but increase mean
completion slots and LLM deliberations. This validates communication savings
within this small exploratory cohort, not an overall efficiency improvement.

All 16 training and 96 evaluation missions complete, with zero backend fallbacks.
Together they contain 7,430 LLM decisions: 7,219 online requests and 211 cache
hits, excluding two warmup requests. Every recorded online decision used exactly one
HTTP request. The source SHA-256 recorded for both campaigns is
`9e18154594aa250245d3eb36e481c8dc16f26aa32b21b0b1b1149bdb48333e16`.

## Frozen calibration

Each model uses its own eight default-scenario training missions, seeds
`6000..6007`. Parameters minimize target NLL sampled every five slots and are
frozen before evaluation. Both arms use MICA, communication price `1e-5`, and
100 available symbols per agent per slot. Baseline temperature is 0.1 and
persistence is zero for every receiver.

| Model | Temperatures, agents 0..5 | Public-target persistence, agents 0..5 |
| --- | --- | --- |
| Qwen3 8B | 0.8, 0.2, 0.8, 0.1, 0.8, 0.1 | 8, 4, 8, 4, 4, 0 |
| Llama 3.1 8B | 0.8, 0.2, 0.8, 0.2, 0.8, 0.1 | 8, 4, 8, 4, 8, 0 |

The selected LLM temperatures are at the grid's upper bound, and several
persistence bonuses are also at their upper bound. They are optima within the
fixed candidate grid, not global optima. Agent-specific parameters can reflect
planning priority and available announcements as well as model behavior.

## Mission outcomes

Each row compares 12 paired seeds, `7000..7011`. Slots are simulated completion
time; symbols are actual uplink use. Positive slot changes mean slower missions.

| Model | Scenario | Baseline slots | Calibrated slots | Slot change | Baseline symbols | Calibrated symbols | Symbol change |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 8B | Default | 72.25 | 89.00 | +23.2% | 12,622.08 | 9,640.00 | -23.6% |
| Qwen3 8B | Clustered | 52.42 | 62.50 | +19.2% | 10,132.08 | 7,242.42 | -28.5% |
| Llama 3.1 8B | Default | 91.42 | 121.58 | +33.0% | 15,266.67 | 9,847.50 | -35.5% |
| Llama 3.1 8B | Clustered | 54.33 | 60.08 | +10.6% | 10,474.67 | 6,212.25 | -40.7% |

Paired bootstrap differences below are calibrated minus baseline. Intervals use
10,000 seed resamples and are unadjusted for multiple exploratory comparisons.

| Model | Scenario | Slot difference, 95% interval | Symbol difference, 95% interval |
| --- | --- | --- | --- |
| Qwen3 8B | Default | +16.75 [-1.92, +35.83] | -2,982.08 [-4,796.84, -1,266.08] |
| Qwen3 8B | Clustered | +10.08 [-9.00, +28.17] | -2,889.67 [-5,818.18, -454.22] |
| Llama 3.1 8B | Default | +30.17 [+6.25, +53.92] | -5,419.17 [-8,411.84, -2,723.10] |
| Llama 3.1 8B | Clustered | +5.75 [-10.75, +24.50] | -4,262.42 [-6,044.27, -2,622.95] |

## Prediction diagnostics

NLL is measured on held-out baseline trajectories in each indicated scenario.
The table isolates the three LLM receivers; lower is better. It is not the
likelihood of generated text or a measure of intrinsic language-model quality.

| Model | Scenario | Baseline LLM target NLL | Calibrated LLM target NLL |
| --- | --- | ---: | ---: |
| Qwen3 8B | Default | 9.0821 | 5.2817 |
| Qwen3 8B | Clustered | 9.6467 | 4.9510 |
| Llama 3.1 8B | Default | 8.9695 | 4.9975 |
| Llama 3.1 8B | Clustered | 9.9193 | 4.7364 |

All-receiver NLL also falls: Qwen3 default 6.7489 to 4.6386, clustered 6.9470 to
4.3825; Llama default 6.7074 to 4.3528, clustered 7.1797 to 4.3342. Separate
classical-receiver and per-agent values are preserved in each `summary.json`.

Better prediction of observed targets does not establish accurate prediction of
how a teammate would respond to a hypothetical message. In particular, the
full-grid predictor approximates an LLM planner that chooses among five targets
and retains its previous intention between replans. Minimizing observational
NLL can select a flatter distribution without improving message valuation.

## Inference accounting

Counts below sum 12 evaluation missions in each arm. Decisions include cached
choices; HTTP requests count actual online inference. Server seconds are Ollama's
reported total duration for those requests. Warmup and training are excluded.

| Model | Scenario | Arm | Decisions | Cache hits | HTTP requests | Server seconds |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Qwen3 8B | Default | Baseline | 774 | 25 | 749 | 189.39 |
| Qwen3 8B | Default | Calibrated | 916 | 27 | 889 | 224.49 |
| Qwen3 8B | Clustered | Baseline | 608 | 28 | 580 | 145.53 |
| Qwen3 8B | Clustered | Calibrated | 687 | 23 | 664 | 166.05 |
| Llama 3.1 8B | Default | Baseline | 919 | 26 | 893 | 333.78 |
| Llama 3.1 8B | Default | Calibrated | 1,180 | 26 | 1,154 | 432.66 |
| Llama 3.1 8B | Clustered | Baseline | 590 | 30 | 560 | 209.27 |
| Llama 3.1 8B | Clustered | Calibrated | 623 | 26 | 597 | 222.44 |

Shared response caches make these timings unsuitable for a controlled online
latency comparison. The increased decision counts are nevertheless an observed
increase in planner deliberations under the changed mission trajectories.

## Interpretation

Both models save communication in both tested scenarios, with unadjusted symbol
intervals below zero, but have worse mean completion slots and more LLM decisions.
Llama's default-scenario slot interval is entirely above zero, indicating a
slowdown in this exploratory comparison. The other three slot intervals include
zero: they establish neither a population-level slowdown nor a speedup. All
observed completion rates are 100%, but that does not establish completion-time
non-inferiority. This is a resource tradeoff, not an established overall
efficiency improvement. Twelve pairs per comparison and unadjusted intervals
limit the strength of generalization.

A plausible mechanism is that higher temperature and target persistence reduce
the estimated value of messages, suppressing useful as well as redundant
communication. This is an explanation to test, not a measured causal result.
Calibrating only observational NLL is insufficient to justify adopting the
change as the default. Future calibration should check task loss or completion
constraints on separate validation seeds, then use fresh test seeds.
The unchanged default remains preferable when adopting a general policy;
receiver calibration stays opt-in.

## Reproduce

```bash
python -m experiments.run_llm_calibration \
  --windows-python /mnt/c/Users/Administrator/AppData/Local/Programs/Python/Python311/python.exe
```

Use the existing WSL Python environment with this repository on `PYTHONPATH=src`
when the package is not installed there. If Ollama is directly accessible, omit
`--windows-python`. The default endpoint is `http://127.0.0.1:11434`; IPv4 avoids
the measured two-second Windows `localhost` IPv6 connection fallback.

Both arms use `think: false`, deterministic decoding, a 1024-token context,
12-token output limit, and the same structured choice schema. Generated response
caches are our own, in the fresh campaign directory; no external cache is used.

Raw training, mission records, cache responses, and aggregate JSON are local in
`results/llm_behavior_calibration/{qwen3_8b,llama3.1_8b}/`, ignored by Git. Model
digests begin `500a1f067a9f` and `46e0c10c039e`, respectively. Resume requires
matching source, model digest, seeds, and settings. Replaying cached decisions
can reproduce mission metrics, but cannot reproduce online inference timings.
