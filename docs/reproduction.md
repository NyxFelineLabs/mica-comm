# Reproduction workflow

The deterministic simulator does not need an LLM or a network connection.

```bash
python -m pip install -e ".[dev]"
python -m pytest -q
python -m mosaic_comm.simulator --scheme gosc --seed 0
python -m experiments.run_all --seeds 100
python -m experiments.plot
```

The original paper campaign also includes revision, realistic-resource, scheduler,
belief-divergence, and heterogeneous LLM experiments. Their runners are kept in
`experiments/` and accept `--seeds` where the campaign is long running. Use a small
seed count first and keep the resulting files in the ignored `results/` directory.

For a fair comparison, keep the same seed set and `Config` values for every scheme.
The simulator uses common random numbers: a seed fixes the world, launch positions,
sensing draws, and channel draws shared by the schemes in that mission.

The reference configuration's seed-0 GOSC mission should complete in 122 slots and
use 13,304 uplink symbols. This is a quick smoke check after installation.

