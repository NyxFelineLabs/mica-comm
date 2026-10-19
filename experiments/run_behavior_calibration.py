"""Fit receiver softmax parameters on training seeds and evaluate held-out missions.

Only the teammate predictor changes. Training labels are instrumented planner
targets; predictor features contain shared beliefs, public positions and public
intentions only. Private targets are labels, never runtime predictor inputs.
"""

import argparse
import json
import time
from dataclasses import asdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np

from mica_comm import Config, Simulation, run_episode
from mica_comm.agents.voi import TeamModel
from mica_comm.core.paths import RESULTS_DIR

TEMPERATURES = (0.02, 0.04, 0.07, 0.1, 0.2, 0.4, 0.8)
PERSISTENCE = (0.0, 1.0, 2.0, 4.0, 8.0)
PARAMETERS = tuple((t, k) for t in TEMPERATURES for k in PERSISTENCE)
VARIANTS = ("baseline", "temperature", "persistence", "calibrated")
SCENARIOS = {
    "default": {},
    "bandwidth50": {"symbols_per_slot": 50},
    "clustered": {"victim_layout": "clustered"},
    "snr-5": {"snr_ref_db": -5},
}


def prediction_losses(sim):
    """Cross-entropy for all calibration candidates on one public snapshot."""
    n = sim.cfg.n_agents
    losses = np.zeros((n, len(PARAMETERS)))
    for j in range(n):
        sender = sim.agents[(j + 1) % n]
        team = TeamModel(sim.view(sender), sender, sim.cfg.tom_temperature)
        score = team.mass_shared * team.dist[j] * team.rep_known[j]
        maximum = float(score.max())
        normalized = (score.reshape(-1) / maximum) if maximum > 0 else np.zeros(score.size)
        target = sim.agents[j].target
        known = sim.view(sender).team_intent.get(j)
        for column, (temperature, persistence) in enumerate(PARAMETERS):
            logits = normalized / temperature
            if known is not None:
                logits[known] += persistence
            offset = float(logits.max())
            losses[j, column] = offset + np.log(np.exp(logits - offset).sum()) - logits[target]
    return losses


def collect_job(job):
    seed, interval = job
    sim = Simulation(Config(), "mica", seed)
    sim._start()
    losses = np.zeros((sim.cfg.n_agents, len(PARAMETERS)))
    samples = 0
    for t in range(sim.cfg.max_steps):
        sim.phase_decide(t)
        if t % interval == 0:
            losses += prediction_losses(sim)
            samples += 1
        if sim.phase_communicate(t):
            break
    return {"seed": seed, "loss_sums": losses.tolist(), "samples_per_agent": samples}


def fit(records):
    losses = np.sum([r["loss_sums"] for r in records], axis=0)
    selected = {}
    for variant in VARIANTS:
        allowed = [
            i
            for i, (temperature, persistence) in enumerate(PARAMETERS)
            if (variant not in ("baseline", "persistence") or temperature == 0.1)
            and (variant not in ("baseline", "temperature") or persistence == 0)
        ]
        selected[variant] = [allowed[int(np.argmin(row[allowed]))] for row in losses]
    return selected


def mission_job(job):
    scenario, variant, seed, indices = job
    overrides = SCENARIOS[scenario]
    if variant != "baseline":
        overrides = {
            **overrides,
            "tom_temperatures": tuple(PARAMETERS[i][0] for i in indices),
            "tom_persistence": tuple(PARAMETERS[i][1] for i in indices),
        }
    started = time.monotonic()
    result = run_episode(Config().with_(**overrides), "mica", seed)
    result.pop("curve")
    return {
        "scenario": scenario,
        "variant": variant,
        "seed": seed,
        "elapsed_seconds": time.monotonic() - started,
        **result,
    }


def paired_interval(values, rng):
    values = np.asarray(values, dtype=float)
    draws = values[rng.integers(0, len(values), size=(10000, len(values)))].mean(axis=1)
    return {"mean": float(values.mean()), "ci95": np.percentile(draws, [2.5, 97.5]).tolist()}


def summarize(rows):
    rng = np.random.default_rng(5821)
    summary = {}
    for scenario in sorted({r["scenario"] for r in rows}):
        baseline = {
            r["seed"]: r for r in rows if r["scenario"] == scenario and r["variant"] == "baseline"
        }
        summary[scenario] = {}
        for variant in VARIANTS:
            selected = sorted(
                (r for r in rows if r["scenario"] == scenario and r["variant"] == variant),
                key=lambda r: r["seed"],
            )
            summary[scenario][variant] = {
                "n": len(selected),
                "completion_rate": float(np.mean([r["completed"] for r in selected])),
                "completion_slots": float(np.mean([r["completion_time"] for r in selected])),
                "uplink_symbols": float(np.mean([r["symbols"] for r in selected])),
                "slot_difference": paired_interval(
                    [
                        r["completion_time"] - baseline[r["seed"]]["completion_time"]
                        for r in selected
                    ],
                    rng,
                ),
                "symbol_difference": paired_interval(
                    [r["symbols"] - baseline[r["seed"]]["symbols"] for r in selected], rng
                ),
            }
    return summary


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-seeds", type=int, default=16)
    parser.add_argument("--eval-seeds", type=int, default=30)
    parser.add_argument("--train-start", type=int, default=1000)
    parser.add_argument("--eval-start", type=int, default=3000)
    parser.add_argument("--sample-interval", type=int, default=5)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "behavior_calibration")
    args = parser.parse_args()
    if min(args.train_seeds, args.eval_seeds, args.sample_interval, args.workers) <= 0:
        parser.error("seed counts, sample interval, and worker count must be positive")
    train_seeds = list(range(args.train_start, args.train_start + args.train_seeds))
    eval_seeds = list(range(args.eval_start, args.eval_start + args.eval_seeds))
    if set(train_seeds) & set(eval_seeds):
        parser.error("training and evaluation seeds must be disjoint")
    training_path = args.output / "training.json"
    if training_path.exists():
        training = json.loads(training_path.read_text(encoding="utf-8"))
        if training["seeds"] != train_seeds or training["sample_interval"] != args.sample_interval:
            parser.error(
                "existing training data has different settings; choose another output directory"
            )
    else:
        with Pool(args.workers) as pool:
            records = list(pool.imap(collect_job, [(s, args.sample_interval) for s in train_seeds]))
        training = {
            "seeds": train_seeds,
            "sample_interval": args.sample_interval,
            "records": records,
        }
        save(training_path, training)
    selected = fit(training["records"])
    calibration = {
        v: {"indices": ids, "parameters": [PARAMETERS[i] for i in ids]}
        for v, ids in selected.items()
    }
    save(args.output / "calibration.json", calibration)
    print("Frozen calibration:", json.dumps(calibration), flush=True)
    validation_path = args.output / "prediction_validation.json"
    with Pool(args.workers) as pool:
        validation = list(pool.imap(collect_job, [(s, args.sample_interval) for s in eval_seeds]))
    loss_sums = np.sum([r["loss_sums"] for r in validation], axis=0)
    samples = sum(r["samples_per_agent"] for r in validation) * Config.n_agents
    nll = {
        v: float(sum(loss_sums[j, i] for j, i in enumerate(ids)) / samples)
        for v, ids in selected.items()
    }
    save(validation_path, {"seeds": eval_seeds, "nll": nll, "records": validation})
    print("Held-out prediction NLL:", json.dumps(nll), flush=True)
    rows_path = args.output / "missions.jsonl"
    existing = (
        [json.loads(line) for line in rows_path.read_text().splitlines()]
        if rows_path.exists()
        else []
    )
    done = {(r["scenario"], r["variant"], r["seed"]) for r in existing}
    jobs = [
        (scenario, variant, seed, selected[variant])
        for scenario in args.scenarios
        for seed in eval_seeds
        for variant in VARIANTS
        if (scenario, variant, seed) not in done
    ]
    with Pool(args.workers) as pool, rows_path.open("a", encoding="utf-8") as stream:
        for count, row in enumerate(pool.imap_unordered(mission_job, jobs), 1):
            existing.append(row)
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            if count % 20 == 0 or count == len(jobs):
                print(f"Missions: {count}/{len(jobs)}", flush=True)
    rows = [r for r in existing if r["scenario"] in args.scenarios and r["seed"] in eval_seeds]
    report = {
        "config": asdict(Config()),
        "training_seeds": train_seeds,
        "evaluation_seeds": eval_seeds,
        "calibration": calibration,
        "prediction_nll": nll,
        "results": summarize(rows),
    }
    save(args.output / "summary.json", report)
    print(json.dumps(report["results"], indent=2), flush=True)


if __name__ == "__main__":
    main()
