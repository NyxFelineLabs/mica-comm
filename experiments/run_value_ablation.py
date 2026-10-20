"""Matched-seed comparison of ToM and task-weighted information gain.

Example:
    python -m experiments.run_value_ablation --seeds 12 --workers 6
"""

import argparse
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from mica_comm import Config
from mica_comm.core.paths import RESULTS_DIR
from mica_comm.simulation.realistic import RealisticSimulation

POLICIES = ("mica", "mica_aoi", "mica_bits", "mica_ptr", "mica_twig", "mica_ig", "genie")


def _job(job):
    policy, seed, cfg = job
    result = RealisticSimulation(cfg, policy, seed).run()
    result.pop("curve", None)
    return {"policy": policy, "seed": seed, **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--seed-start", type=int, default=9000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--price", type=float, default=Config.energy_price)
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "value_ablation")
    args = parser.parse_args()
    if args.seeds < 2 or args.workers < 1:
        parser.error("at least two seeds and one worker are required")
    if args.price <= 0:
        parser.error("price must be positive")
    cfg = Config(energy_price=args.price)
    jobs = [
        (policy, seed, cfg)
        for seed in range(args.seed_start, args.seed_start + args.seeds)
        for policy in POLICIES
    ]
    args.output.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(_job, jobs))
    (args.output / "missions.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )
    for policy in POLICIES:
        subset = [row for row in rows if row["policy"] == policy]
        completion = sum(row["completion_time"] for row in subset) / len(subset)
        symbols = sum(row["total_symbols"] for row in subset) / len(subset)
        completed = sum(row["completed"] for row in subset) / len(subset)
        print(
            f"{policy}: completion={completion:.2f}, total_symbols={symbols:.2f}, "
            f"completed={completed:.1%}"
        )


if __name__ == "__main__":
    main()
