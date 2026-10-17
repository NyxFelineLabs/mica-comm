"""Compare communication policies with three installed LLM team configurations.

Each mission has three agents using one selected LLM and three classical
planners. Default MICA parameters are used without receiver calibration.
"""

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import numpy as np

from experiments.run_behavior_calibration import SCENARIOS, paired_interval, save
from experiments.run_llm_calibration import (
    OllamaTransport,
    check_manifest,
    mission,
    read_rows,
)
from mica_comm import Config, llm_agent
from mica_comm.llm_agent import LLMClient
from mica_comm.paths import RESULTS_DIR

MODELS = ("qwen3:8b", "llama3.1:8b", "gemma3:12b")
POLICIES = ("sem", "mica", "genie")


def summarize(rows):
    """Summarize absolute outcomes and paired MICA-minus-periodic differences."""
    rng = np.random.default_rng(5821)
    report = {}
    for scenario in sorted({r["scenario"] for r in rows}):
        subset = [r for r in rows if r["scenario"] == scenario]
        periodic = {r["seed"]: r for r in subset if r["scheme"] == "sem"}
        report[scenario] = {}
        for policy in POLICIES:
            group = sorted((r for r in subset if r["scheme"] == policy), key=lambda r: r["seed"])
            if not group:
                continue
            entry = {
                "n": len(group),
                "completion_rate": float(np.mean([r["completed"] for r in group])),
                "completion_slots": float(np.mean([r["completion_time"] for r in group])),
                "uplink_symbols": float(np.mean([r["symbols"] for r in group])),
                "uplink_bits": float(np.mean([r["bits"] for r in group])),
                "llm_decisions": sum(r["llm_decisions"] for r in group),
                "llm_fallbacks": sum(r["llm_fallbacks"] for r in group),
                "elapsed_seconds": sum(r["elapsed_seconds"] for r in group),
                "inference": {
                    k: sum(r["inference"][k] for r in group) for k in group[0]["inference"]
                },
            }
            if policy == "mica":
                if any(r["seed"] not in periodic for r in group):
                    raise ValueError("MICA comparison requires the matching periodic seeds")
                entry["slot_difference_vs_sem"] = paired_interval(
                    [r["completion_time"] - periodic[r["seed"]]["completion_time"] for r in group],
                    rng,
                )
                entry["symbol_difference_vs_sem"] = paired_interval(
                    [r["symbols"] - periodic[r["seed"]]["symbols"] for r in group], rng
                )
            report[scenario][policy] = entry
    return report


def campaign(args, model, digest, transport):
    cfg = Config(llm_agents=(0, 2, 4), llm_model=model)
    output = args.output / model.replace(":", "_")
    seeds = list(range(args.seed_start, args.seed_start + args.seeds))
    root = Path(__file__).resolve().parents[1]
    files = sorted((root / "src/mica_comm").glob("*.py")) + [
        Path(__file__).resolve(),
        root / "experiments/run_llm_calibration.py",
        root / "experiments/run_behavior_calibration.py",
    ]
    manifest = {
        "protocol": "team-benchmark-v1",
        "source_sha256": hashlib.sha256(b"".join(p.read_bytes() for p in files)).hexdigest(),
        "model": model,
        "model_digest": digest,
        "ollama_version": transport.request("/api/version")["version"],
        "config": asdict(cfg),
        "generation": {
            "think": False,
            "temperature": 0,
            "seed": 0,
            "num_predict": 12,
            "num_ctx": 1024,
        },
        "seeds": seeds,
        "scenarios": args.scenarios,
        "policies": POLICIES,
    }
    manifest = json.loads(json.dumps(manifest))
    check_manifest(output / "manifest.json", manifest)
    client = LLMClient(model, cache_dir=str(output / "cache"), transport=transport)
    llm_agent._CLIENTS[model] = client
    if client.choose("Return JSON with choice A.", ["A"]) != "A":
        raise RuntimeError(f"Warmup failed for {model}")
    path = output / "missions.jsonl"
    rows = read_rows(path)
    done = {(r["scenario"], r["scheme"], r["seed"]) for r in rows}
    expected = len(args.scenarios) * len(seeds) * len(POLICIES)
    with path.open("a", encoding="utf-8") as stream:
        for scenario in args.scenarios:
            for index, seed in enumerate(seeds):
                # Each policy appears first equally often when the seed count
                # is divisible by three. Shared caches are never latency evidence.
                offset = index % len(POLICIES)
                ordered = POLICIES[offset:] + POLICIES[:offset]
                for policy in ordered:
                    if (scenario, policy, seed) in done:
                        continue
                    row = mission(
                        cfg.with_(**SCENARIOS[scenario]),
                        seed,
                        client,
                        transport,
                        interval=5,
                        scheme=policy,
                    )
                    row.update(model=model, scenario=scenario, scheme=policy)
                    rows.append(row)
                    stream.write(json.dumps(row) + "\n")
                    stream.flush()
                    print(
                        f"{model} {len(rows)}/{expected} {scenario} {policy} seed={seed} "
                        f"slots={row['completion_time']} symbols={row['symbols']} "
                        f"calls={row['inference']['http_requests']} "
                        f"hits={row['inference']['cache_hits']} complete={row['completed']}",
                        flush=True,
                    )
    keys = {(r["scenario"], r["scheme"], r["seed"]) for r in rows}
    if len(rows) != expected or len(keys) != expected:
        raise ValueError("Incomplete or duplicate benchmark records")
    report = {"manifest": manifest, "results": summarize(rows)}
    save(output / "summary.json", report)
    print(json.dumps({model: report["results"]}, indent=2), flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=list(MODELS))
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--seed-start", type=int, default=8000)
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=["default"])
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "team_benchmark")
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--windows-python", help="WSL path to Windows python.exe")
    args = parser.parse_args()
    if args.seeds <= 0:
        parser.error("seed count must be positive")
    if len(set(args.models)) != len(args.models) or len(set(args.scenarios)) != len(args.scenarios):
        parser.error("models and scenarios must not contain duplicates")
    transport = OllamaTransport(args.url, args.windows_python)
    try:
        installed = {m["name"]: m["digest"] for m in transport.request("/api/tags")["models"]}
        for model in args.models:
            if model not in installed:
                parser.error(f"Model not installed: {model}")
        reports = {}
        for model in args.models:
            reports[model] = campaign(args, model, installed[model], transport)
        save(args.output / "summary.json", reports)
    finally:
        transport.close()


if __name__ == "__main__":
    main()
