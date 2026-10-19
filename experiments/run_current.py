"""Run a fresh, seeded campaign for the current executable mission simulator.

python -m experiments.run_current --seeds 12 --workers 6 --output results/current
"""

import argparse
import json
import multiprocessing
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

from mica_comm import Config
from mica_comm.agents.llm_agent import LLMClient
from mica_comm.core.config import MIXED_TEAM_MODELS
from mica_comm.core.paths import RESULTS_DIR
from mica_comm.core.provenance import source_fingerprint
from mica_comm.simulation.realistic import RealisticSimulation

POLICIES = ("sem", "mica", "genie")
MODELS = MIXED_TEAM_MODELS
_CLIENTS = {}
_TRANSPORT = None


class CampaignLLMClient(LLMClient):
    """Share responses between workers and serialize writes for each model."""

    def __init__(self, model, cache_dir, transport, cache, lock):
        super().__init__(model, cache_dir=cache_dir, transport=transport)
        self.cache = cache
        self.lock = lock

    def choose(self, prompt, labels):
        with self.lock:
            return super().choose(prompt, labels)


def design(team="mixed"):
    """Freeze settings before evaluation; each setting uses the same mission seeds."""
    base = Config(shared_budget=300, shared_mode="static")
    if team == "mixed":
        base = base.with_(llm_agents=(0, 2, 4), llm_models=MODELS)
    elif team != "planner":
        raise ValueError(f"Unknown team: {team}")
    cells = [("default", 0, policy, base) for policy in POLICIES]
    sweeps = (
        ("agents", "n_agents", (6, 8, 10, 12, 14) if team == "mixed" else (2, 4, 6, 8, 10)),
        ("budget", "symbols_per_slot", (25, 50, 100, 200)),
        ("snr", "snr_ref_db", (-10, -5, 0, 5, 10, 20)),
        ("downlink_loss", "dl_loss", (0.0, 0.1, 0.3, 0.5)),
        ("downlink_delay", "dl_delay", (0, 1, 3, 5)),
        ("shared", "shared_budget", (150, 300, 600)),
    )
    for experiment, field, values in sweeps:
        for value in values:
            for policy in POLICIES if experiment != "shared" else ("sem", "mica"):
                if experiment == "budget":
                    cfg = base.with_(shared_budget=value * base.n_agents)
                elif experiment == "shared":
                    cfg = base.with_(shared_budget=value, shared_mode="price")
                else:
                    cfg = base.with_(**{field: value})
                cells.append((experiment, value, policy, cfg))
    for task in ("search", "rescue"):
        for mode in ("static", "price", "central"):
            cfg = base.with_(shared_mode=mode)
            if task == "rescue":
                cfg = cfg.with_(task="rescue", deadline_min=60, deadline_max=180)
            cells.append(("coordinator", f"{task}_{mode}", "mica", cfg))
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
                        task="rescue",
                        deadline_min=60,
                        deadline_max=180,
                        symbols_per_slot=budget,
                        shared_mode="price",
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


def init_llm(url, cache_dir, caches, locks):
    """Each worker keeps all three models and digest-isolated response caches."""
    from experiments.run_llm_calibration import OllamaTransport
    from mica_comm.agents import llm_agent

    global _TRANSPORT, _CLIENTS
    _TRANSPORT = OllamaTransport(url)
    for model in MODELS:
        client = CampaignLLMClient(model, cache_dir, _TRANSPORT, caches[model], locks[model])
        llm_agent._CLIENTS[model] = client
        _CLIENTS[model] = client


def inference_counters():
    from experiments.run_llm_calibration import counters

    return {model: counters(client, _TRANSPORT) for model, client in _CLIENTS.items()}


def _key(row):
    return row["experiment"], row["parameter"], row["scheme"], row["seed"]


def _job(job):
    experiment, parameter, policy, cfg, seed = job
    started = time.perf_counter()
    before = inference_counters()
    sim = RealisticSimulation(cfg, policy, seed, record_traj=experiment == "default")
    sim._start()
    for t in range(cfg.max_steps):
        sim.phase_decide(t)
        if any(getattr(a, "fallbacks", 0) for a in sim.agents):
            raise RuntimeError(f"LLM fallback: {experiment}/{parameter}/{policy}/{seed}, slot {t}")
        if sim.phase_communicate(t):
            break
    result = sim.result()
    if before:
        after = inference_counters()
        # Transport totals are shared between the three clients, so record once.
        result["inference"] = {
            "by_model": {
                model: {
                    k: after[model][k] - before[model][k]
                    for k in ("cache_hits", "cache_misses", "client_seconds")
                }
                for model in before
            },
            **{
                k: after[MODELS[0]][k] - before[MODELS[0]][k]
                for k in ("http_requests", "server_seconds", "prompt_tokens", "generated_tokens")
            },
        }
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--seed-start", type=int, default=9000)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--team", choices=("mixed", "planner"), default="mixed")
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--table-xii", action="store_true", help="Also run the orthogonal search reference"
    )
    parser.add_argument(
        "--only", nargs="+", help="Explicit subset for diagnostics; omitted runs the full design"
    )
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "current_mixed")
    args = parser.parse_args(argv)
    if args.seeds < 2 or args.workers < 1:
        parser.error("at least two seeds and one worker are required")
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    cells = design(args.team)
    if args.table_xii:
        cfg = cells[0][3].with_(shared_budget=0)
        cells = [("table_xii", 0, policy, cfg) for policy in POLICIES] + cells
    if args.only:
        unknown = set(args.only) - {cell[0] for cell in cells}
        if unknown:
            parser.error(f"Unknown experiments: {sorted(unknown)}")
        cells = [cell for cell in cells if cell[0] in args.only]
    backend = {}
    if args.team == "mixed":
        from experiments.run_llm_calibration import OllamaTransport

        transport = OllamaTransport(args.url)
        try:
            installed = {m["name"]: m["digest"] for m in transport.request("/api/tags")["models"]}
            if set(MODELS) - set(installed):
                parser.error(f"Missing models: {set(MODELS) - set(installed)}")
            backend = {
                "model_digests": {model: installed[model] for model in MODELS},
                "ollama_version": transport.request("/api/version")["version"],
                "generation": {
                    "think": False,
                    "temperature": 0,
                    "seed": 0,
                    "num_predict": 12,
                    "num_ctx": 1024,
                },
            }
        finally:
            transport.close()
    jobs = [(*cell, seed) for cell in cells for seed in seeds]
    manifest = {
        "protocol": "mica-current-mixed-v2",
        "engine": "RealisticSimulation",
        "team": args.team,
        "llm_agents": list(cells[0][3].llm_agents),
        "llm_models": list(cells[0][3].llm_models),
        "team_size_sweep": (
            "Three fixed LLM agents; vary planner count"
            if args.team == "mixed"
            else "Planners only"
        ),
        **backend,
        "seeds": seeds,
        "expected_rows": len(jobs),
        "design": [
            {"experiment": e, "parameter": p, "scheme": s, "config": asdict(c)}
            for e, p, s, c in cells
        ],
        **source_fingerprint([__file__, Path(__file__).with_name("run_llm_calibration.py")]),
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
    configs = {(e, p, s): json.loads(json.dumps(asdict(c))) for e, p, s, c in cells}
    if (
        len(done) != len(rows)
        or not done <= expected
        or any(
            row["config"] != configs[_key(row)[:3]] or row.get("llm_fallbacks", 0) for row in rows
        )
    ):
        raise ValueError("Duplicate or unexpected mission records")
    jobs = [job for job in jobs if (job[0], job[1], job[2], job[4]) not in done]
    with multiprocessing.Manager() as manager:
        cache_dir = str(args.output / "cache")
        caches = (
            {model: manager.dict(LLMClient(model, cache_dir=cache_dir).cache) for model in MODELS}
            if args.team == "mixed"
            else {}
        )
        locks = {model: manager.RLock() for model in caches}
        run_jobs(args, jobs, records, rows, expected, cache_dir, caches, locks)
    from experiments.summarize_current import write_report

    write_report(args.output)
    print(f"Complete: {len(rows)} missions in {args.output}", flush=True)


def run_jobs(args, jobs, records, rows, expected, cache_dir, caches, locks):
    with (
        ProcessPoolExecutor(
            max_workers=args.workers,
            initializer=init_llm if args.team == "mixed" else None,
            initargs=(args.url, cache_dir, caches, locks) if args.team == "mixed" else (),
        ) as pool,
        records.open("a", encoding="utf-8") as stream,
    ):
        futures = [pool.submit(_job, job) for job in jobs]
        for future in as_completed(futures):
            try:
                row = future.result()
            except BaseException:
                for pending in futures:
                    pending.cancel()
                raise
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            rows.append(row)
            print(
                f"{len(rows)}/{len(expected)} {row['experiment']}/{row['parameter']} "
                f"{row['scheme']} seed={row['seed']} slots={row['completion_time']} "
                f"symbols={row['symbols']} fallbacks={row.get('llm_fallbacks', 0)}",
                flush=True,
            )


if __name__ == "__main__":
    main()
