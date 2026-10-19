"""Train and test EToM, an efficient ToM variant for task-oriented communication.

The receiver-model parameters are fit only on training seeds. Candidate energy
prices are selected on a separate tuning cohort; final comparisons use untouched
evaluation seeds. Metrics include the full uplink-plus-downlink symbol count.

    python -m experiments.run_etom_tradeoff --workers 6 --time-weight 0.8
"""

import argparse
import itertools
import json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

from experiments.run_etom_calibration import PARAMETERS, collect_job, fit
from mica_comm import Config
from mica_comm.core.paths import RESULTS_DIR
from mica_comm.simulation.realistic import RealisticSimulation

PRICE_GRID = (0.0, 3e-6, 1e-5, 3e-5, 1e-4, 3e-4, 1e-3)
METHOD_NAME = "EToM"
# A compact, interpretable set around the calibrated model. This keeps tuning
# affordable while still testing whether modest behavior calibration helps.
MODEL_GRID = ((0.2, 2.0),)


def _mission(job):
    model, price, temperatures, persistence, seed = job
    cfg = Config(
        energy_price=price,
        etom_receiver_temperatures=temperatures,
        etom_intent_persistences=persistence,
    )
    result = RealisticSimulation(cfg, "mica", seed).run()
    result.pop("curve", None)
    return {"model": model, "price": price, "seed": seed, **result}


def _mean(rows):
    return {
        "completion_time": float(np.mean([r["completion_time"] for r in rows])),
        "total_symbols": float(np.mean([r["total_symbols"] for r in rows])),
        "completed_rate": float(np.mean([r["completed"] for r in rows])),
    }


def _paired_difference(rows, reference, metric):
    by_seed = {row["seed"]: row for row in reference}
    delta = np.asarray([row[metric] - by_seed[row["seed"]][metric] for row in rows])
    rng = np.random.default_rng(5821)
    sample = delta[rng.integers(0, len(delta), size=(10000, len(delta)))].mean(axis=1)
    return {
        "mean": float(delta.mean()),
        "ci95": [float(x) for x in np.percentile(sample, [2.5, 97.5])],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-seeds", type=int, default=16)
    parser.add_argument("--tune-seeds", type=int, default=8)
    parser.add_argument("--eval-seeds", type=int, default=30)
    parser.add_argument("--train-start", type=int, default=50000)
    parser.add_argument("--tune-start", type=int, default=51000)
    parser.add_argument("--eval-start", type=int, default=52000)
    parser.add_argument("--sample-interval", type=int, default=5)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument(
        "--time-weight",
        type=float,
        default=0.5,
        help="weight on relative completion time; symbols receive the remaining weight",
    )
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "etom_tradeoff")
    args = parser.parse_args()
    if (
        min(args.train_seeds, args.tune_seeds, args.eval_seeds, args.sample_interval, args.workers)
        < 1
    ):
        parser.error("seed counts, sample interval, and worker count must be positive")
    if not 0.0 <= args.time_weight <= 1.0:
        parser.error("--time-weight must be between 0 and 1")
    cohorts = {
        "training": set(range(args.train_start, args.train_start + args.train_seeds)),
        "tuning": set(range(args.tune_start, args.tune_start + args.tune_seeds)),
        "evaluation": set(range(args.eval_start, args.eval_start + args.eval_seeds)),
    }
    if any(
        cohorts[a] & cohorts[b]
        for a, b in (("training", "tuning"), ("training", "evaluation"), ("tuning", "evaluation"))
    ):
        parser.error("training, tuning and evaluation seed cohorts must be disjoint")

    args.output.mkdir(parents=True, exist_ok=True)
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        training = list(
            pool.map(
                collect_job,
                ((seed, args.sample_interval) for seed in sorted(cohorts["training"])),
            )
        )
    selected = fit(training)["calibrated"]
    ce_temperatures = tuple(PARAMETERS[i][0] for i in selected)
    ce_persistence = tuple(PARAMETERS[i][1] for i in selected)
    model_configs = {
        "etom_default": ((), ()),
        "behavior_calibrated": (ce_temperatures, ce_persistence),
    }
    for temperature, persistence_value in MODEL_GRID:
        model_configs[METHOD_NAME] = (
            (temperature,) * Config.n_agents,
            (persistence_value,) * Config.n_agents,
        )
    frozen_calibration = {
        "training_seeds": sorted(cohorts["training"]),
        "behavior_calibrated_temperatures": ce_temperatures,
        "behavior_calibrated_persistence": ce_persistence,
        "model_grid": MODEL_GRID,
        "time_weight": args.time_weight,
        "tuning_seeds": sorted(cohorts["tuning"]),
        "evaluation_seeds": sorted(cohorts["evaluation"]),
        "price_grid": PRICE_GRID,
    }
    (args.output / "calibration.json").write_text(
        json.dumps(frozen_calibration, indent=2), encoding="utf-8"
    )
    jobs = [
        (model, price, temperatures, persistence, seed)
        for seed in sorted(cohorts["tuning"])
        for model, (temperatures, persistence) in model_configs.items()
        for price in PRICE_GRID
    ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        tuning = list(pool.map(_mission, jobs))
    (args.output / "tuning.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in tuning), encoding="utf-8"
    )

    baseline_rows = [
        r for r in tuning if r["model"] == "etom_default" and r["price"] == Config.energy_price
    ]
    baseline_default = _mean(baseline_rows)
    candidates = []
    for (model, price), rows in itertools.groupby(
        sorted(tuning, key=lambda r: (r["model"], r["price"])),
        key=lambda r: (r["model"], r["price"]),
    ):
        stats = _mean(list(rows))
        candidates.append(
            {
                "model": model,
                "price": price,
                "temperatures": model_configs[model][0],
                "persistence": model_configs[model][1],
                **stats,
            }
        )
    for candidate in candidates:
        candidate["joint_score"] = (
            args.time_weight * candidate["completion_time"] / baseline_default["completion_time"]
            + (1.0 - args.time_weight)
            * candidate["total_symbols"]
            / baseline_default["total_symbols"]
        )
    chosen = min(candidates, key=lambda c: c["joint_score"])
    (args.output / "tuning_selection.json").write_text(
        json.dumps(
            {
                "baseline_default": baseline_default,
                "selected_candidate": chosen,
                "candidate_count": len(candidates),
                "joint_objective": {
                    "time_weight": args.time_weight,
                    "symbol_weight": 1.0 - args.time_weight,
                    "normalized_to": "default EToM at default energy price on tuning seeds",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    eval_specs = [
        ("etom_default", Config.energy_price, (), ()),
        (
            METHOD_NAME,
            chosen["price"],
            chosen["temperatures"],
            chosen["persistence"],
        ),
    ]
    eval_jobs = [
        (model, price, model_temperatures, model_persistence, seed)
        for seed in sorted(cohorts["evaluation"])
        for model, price, model_temperatures, model_persistence in eval_specs
    ]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        evaluation = list(pool.map(_mission, eval_jobs))
    (args.output / "evaluation.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in evaluation), encoding="utf-8"
    )

    groups = {name: [r for r in evaluation if r["model"] == name] for name, *_ in eval_specs}
    reference = groups["etom_default"]
    summary = {
        "method_name": METHOD_NAME,
        "method_full_name": "Efficient Theory of Mind for Task-Oriented Semantic Communication",
        **frozen_calibration,
        "selected_candidate": chosen,
        "joint_objective": {
            "time_weight": args.time_weight,
            "symbol_weight": 1.0 - args.time_weight,
        },
        "evaluation": {
            name: {
                **_mean(rows),
                "vs_baseline_default_completion": _paired_difference(
                    rows, reference, "completion_time"
                ),
                "vs_baseline_default_symbols": _paired_difference(rows, reference, "total_symbols"),
            }
            for name, rows in groups.items()
        },
    }
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary["evaluation"], indent=2), flush=True)


if __name__ == "__main__":
    main()

