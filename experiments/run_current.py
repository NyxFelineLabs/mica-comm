"""Run a fresh, seeded campaign for the current executable mission simulator.

python -m experiments.run_current --seeds 12 --workers 6 --output results/current
"""

import argparse
import json
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
from pathlib import Path

from mica_comm import Config
from mica_comm.core.paths import RESULTS_DIR
from mica_comm.core.provenance import source_fingerprint
from mica_comm.simulation.realistic import RealisticSimulation

POLICIES = ("sem", "mica", "genie")


def design():
    """Freeze settings before evaluation; each setting uses the same mission seeds."""
    base = Config()
    cells = [("default", 0, policy, base) for policy in POLICIES]
    sweeps = (
        ("agents", "n_agents", (2, 4, 6, 8, 10)),
        ("budget", "symbols_per_slot", (25, 50, 100, 200)),
        ("snr", "snr_ref_db", (-10, -5, 0, 5, 10, 20)),
        ("downlink_loss", "dl_loss", (0.0, 0.1, 0.3, 0.5)),
        ("downlink_delay", "dl_delay", (0, 1, 3, 5)),
        ("shared", "shared_budget", (150, 300, 600)),
    )
    for experiment, field, values in sweeps:
        for value in values:
            for policy in POLICIES if experiment != "shared" else ("sem", "mica"):
                cells.append((experiment, value, policy, base.with_(**{field: value})))
    for value in (-5, 0, 5, 10):
        for policy in ("sem", "mica"):
            cells.append(("fbl", value, policy, base.with_(snr_ref_db=value, error_model="fbl")))
    for budget in (25, 50, 100, 200):
        for policy in POLICIES:
            cells.append(
                (
                    "rescue",
                    budget,
                    policy,
                    base.with_(
                        task="rescue", deadline_min=60, deadline_max=180, symbols_per_slot=budget
                    ),
                )
            )
    for noise in (0.0, 0.25, 0.5, 1.0):
        cells.append(
            ("noise", noise, "mica", base.with_(value_mode="lognormal", value_sigma=noise))
        )
    for policy in ("mica", "mica_nofilter", "mica_bits", "mica_aoi"):
        cells.append(("ablation", 0, policy, base))
    return cells


def _key(row):
    return row["experiment"], row["parameter"], row["scheme"], row["seed"]


def _job(job):
    experiment, parameter, policy, cfg, seed = job
    started = time.perf_counter()
    sim = RealisticSimulation(cfg, policy, seed, record_traj=experiment == "default")
    result = sim.run()
    if experiment != "default":
        result.pop("curve", None)
    return {
        "experiment": experiment,
        "parameter": parameter,
        "scheme": policy,
        "seed": seed,
        "config": asdict(cfg),
        "elapsed_seconds": time.perf_counter() - started,
        **result,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--seed-start", type=int, default=9000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "current")
    args = parser.parse_args()
    if args.seeds < 2 or args.workers < 1:
        parser.error("at least two seeds and one worker are required")
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    cells = design()
    jobs = [(*cell, seed) for cell in cells for seed in seeds]
    manifest = {
        "protocol": "mica-current-v1",
        "engine": "RealisticSimulation",
        "llm_agents": [],
        "seeds": seeds,
        "expected_rows": len(jobs),
        "design": [
            {"experiment": e, "parameter": p, "scheme": s, "config": asdict(c)}
            for e, p, s, c in cells
        ],
        **source_fingerprint([__file__]),
    }
    manifest = json.loads(json.dumps(manifest))
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / "manifest.json"
    if path.exists() and json.loads(path.read_text()) != manifest:
        raise ValueError("Source or design changed; use a fresh output directory")
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    records = args.output / "missions.jsonl"
    rows = (
        [json.loads(line) for line in records.read_text().splitlines()] if records.exists() else []
    )
    done = {_key(row) for row in rows}
    expected = {(e, p, s, seed) for e, p, s, _, seed in jobs}
    if len(done) != len(rows) or not done <= expected:
        raise ValueError("Duplicate or unexpected mission records")
    jobs = [job for job in jobs if (job[0], job[1], job[2], job[4]) not in done]
    with (
        ProcessPoolExecutor(max_workers=args.workers) as pool,
        records.open("a", encoding="utf-8") as stream,
    ):
        for row in pool.map(_job, jobs):
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            rows.append(row)
            if len(rows) % 24 == 0:
                print(f"{len(rows)}/{len(expected)} missions", flush=True)
    print(f"Complete: {len(rows)} missions in {args.output}", flush=True)


if __name__ == "__main__":
    main()
