# Three planners + three different LLMs

Validated 1380/1380 missions; backend fallbacks: 0.

LLM agents 0 / 2 / 4 use Qwen3 8B / Llama 3.1 8B / Gemma 3 12B respectively.

This extends Table XII to three different models in one team and uses the current EToM and exact DP scheduler. It does not reproduce the paper's original model tags or numerical results.

Team-size sweeps retain three LLMs and vary the number of planners. Failed missions remain in the cohort at the simulation horizon. Time is measured in simulation slots.

## table_xii

Orthogonal uplinks, 100 symbols per agent per slot.

| Scheme | Missions | Time [95% CI] | Uplink symbols | Total symbols | Completion |
| --- | ---: | --- | ---: | ---: | ---: |
| genie | 12 | 74.00 [62.17, 86.34] | 0.00 | 10492.42 | 100.0% |
| mica | 12 | 83.08 [67.50, 101.00] | 12924.25 | 16943.17 | 100.0% |
| sem | 12 | 91.75 [69.08, 117.00] | 47989.75 | 55429.83 | 100.0% |

Paired periodic − MICA time: 8.67 [-20.00, 38.34] slots. Positive means MICA is faster.

Periodic / MICA uplink symbols: 3.71 [2.65, 5.05].

## default

Shared 300-symbol uplink, static equal shares.

| Scheme | Missions | Time [95% CI] | Uplink symbols | Total symbols | Completion |
| --- | ---: | --- | ---: | ---: | ---: |
| genie | 12 | 74.00 [62.17, 86.34] | 0.00 | 10492.42 | 100.0% |
| mica | 12 | 108.50 [81.67, 138.75] | 8685.83 | 12217.17 | 100.0% |
| sem | 12 | 90.50 [73.83, 109.42] | 24267.17 | 27934.25 | 100.0% |

Paired periodic − MICA time: -18.00 [-56.17, 18.25] slots. Positive means MICA is faster.

Periodic / MICA uplink symbols: 2.79 [2.11, 3.63].

