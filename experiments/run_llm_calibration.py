"""Validate frozen teammate softmax calibration with locally served LLM teams.

Each team contains three LLM agents (0, 2, 4) and three classical planners.
Only the receiver softmax parameters differ between the two evaluation arms.
Own response caches are isolated by protocol and model digest. Cached latency
is recorded for accounting and must not be interpreted as online speedup.
"""

import argparse
import hashlib
import json
import subprocess
import time
import urllib.request
from dataclasses import asdict
from pathlib import Path

import numpy as np

from experiments.run_etom_calibration import (
    PARAMETERS,
    SCENARIOS,
    fit,
    paired_interval,
    prediction_losses,
    save,
)
from mica_comm import Config, Simulation, llm_agent
from mica_comm.agents.llm_agent import LLMClient
from mica_comm.core.paths import RESULTS_DIR

# A persistent Windows subprocess lets WSL reach an Ollama server bound to
# Windows localhost without changing the server or exposing a network port.
WINDOWS_BRIDGE = """
import json, sys, urllib.request
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
for line in sys.stdin:
    try:
        call = json.loads(line)
        body = call['body']
        request = urllib.request.Request(
            call['url'], None if body is None else json.dumps(body).encode(),
            {'Content-Type': 'application/json'})
        with opener.open(request, timeout=300) as response:
            result = {'result': json.load(response)}
    except Exception as error:
        result = {'error': str(error)}
    print(json.dumps(result), flush=True)
"""


class OllamaTransport:
    """HTTP transport with optional WSL interop and server timing counters."""

    def __init__(self, url, windows_python=None):
        self.url = url.rstrip("/")
        self.bridge = (
            subprocess.Popen(
                [windows_python, "-u", "-c", WINDOWS_BRIDGE],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
            )
            if windows_python
            else None
        )
        self.requests = 0
        self.server_seconds = 0.0
        self.prompt_tokens = 0
        self.generated_tokens = 0

    def request(self, path, body=None):
        url = self.url + path
        if self.bridge:
            self.bridge.stdin.write(json.dumps({"url": url, "body": body}) + "\n")
            self.bridge.stdin.flush()
            line = self.bridge.stdout.readline()
            if not line:
                raise RuntimeError("Windows Ollama bridge exited unexpectedly")
            reply = json.loads(line)
            if "error" in reply:
                raise RuntimeError(reply["error"])
            return reply["result"]
        request = urllib.request.Request(
            url,
            None if body is None else json.dumps(body).encode(),
            {"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=300) as response:
            return json.load(response)

    def __call__(self, body):
        # Qwen3 must not spend its short structured-output budget on reasoning.
        # The same non-thinking setting is used in both evaluation arms.
        self.requests += 1
        result = self.request("/api/generate", {**body, "think": False})
        self.server_seconds += result.get("total_duration", 0) / 1e9
        self.prompt_tokens += result.get("prompt_eval_count", 0)
        self.generated_tokens += result.get("eval_count", 0)
        return result

    def close(self):
        if self.bridge:
            self.bridge.stdin.close()
            self.bridge.wait(timeout=10)


def counters(client, transport):
    return {
        "cache_hits": client.hits,
        "cache_misses": client.calls,
        "client_seconds": client.seconds,
        "http_requests": transport.requests,
        "server_seconds": transport.server_seconds,
        "prompt_tokens": transport.prompt_tokens,
        "generated_tokens": transport.generated_tokens,
    }


def mission(cfg, seed, client, transport, interval, collect=False, scheme="mica"):
    """Run one mission, rejecting backend failures before continuing a trajectory."""
    before = counters(client, transport)
    started = time.monotonic()
    sim = Simulation(cfg, scheme, seed)
    sim._start()
    losses = np.zeros((cfg.n_agents, len(PARAMETERS)))
    samples = 0
    for t in range(cfg.max_steps):
        sim.phase_decide(t)
        if any(getattr(agent, "fallbacks", 0) for agent in sim.agents):
            raise RuntimeError(f"LLM fallback at seed {seed}, slot {t}; mission rejected")
        if collect and t % interval == 0:
            losses += prediction_losses(sim)
            samples += 1
        if sim.phase_communicate(t):
            break
    result = sim.result()
    result.pop("curve")
    result.update(
        seed=seed,
        elapsed_seconds=time.monotonic() - started,
        inference={k: v - before[k] for k, v in counters(client, transport).items()},
    )
    if collect:
        result.update(loss_sums=losses.tolist(), samples_per_agent=samples)
    return result


def summarize(rows, selected, llm_agents):
    """Paired mission intervals and prediction diagnostics on baseline trajectories."""
    rng = np.random.default_rng(5821)
    report = {}
    for scenario in sorted({row["scenario"] for row in rows}):
        baseline = {
            r["seed"]: r for r in rows if r["scenario"] == scenario and r["variant"] == "baseline"
        }
        report[scenario] = {}
        for variant in ("baseline", "calibrated"):
            subset = [r for r in rows if r["scenario"] == scenario and r["variant"] == variant]
            entry = {
                "n": len(subset),
                "completion_rate": float(np.mean([r["completed"] for r in subset])),
                "completion_slots": float(np.mean([r["completion_time"] for r in subset])),
                "uplink_symbols": float(np.mean([r["symbols"] for r in subset])),
                "slot_difference": paired_interval(
                    [r["completion_time"] - baseline[r["seed"]]["completion_time"] for r in subset],
                    rng,
                ),
                "symbol_difference": paired_interval(
                    [r["symbols"] - baseline[r["seed"]]["symbols"] for r in subset], rng
                ),
                "llm_decisions": sum(r["llm_decisions"] for r in subset),
                "llm_fallbacks": sum(r["llm_fallbacks"] for r in subset),
                "elapsed_seconds": sum(r["elapsed_seconds"] for r in subset),
                "inference": {
                    k: sum(r["inference"][k] for r in subset) for k in subset[0]["inference"]
                },
            }
            loss_sums = np.sum([r["loss_sums"] for r in baseline.values()], axis=0)
            samples = sum(r["samples_per_agent"] for r in baseline.values())
            per_agent = [float(loss_sums[j, i] / samples) for j, i in enumerate(selected[variant])]
            entry["prediction_nll"] = {
                "all": float(np.mean(per_agent)),
                "llm": float(np.mean([per_agent[j] for j in llm_agents])),
                "classical": float(
                    np.mean([v for j, v in enumerate(per_agent) if j not in llm_agents])
                ),
                "per_agent": per_agent,
            }
            report[scenario][variant] = entry
    return report


def check_manifest(path, manifest):
    """Prevent resumed runs from silently mixing models, settings, or source."""
    if path.exists() and json.loads(path.read_text(encoding="utf-8")) != manifest:
        raise ValueError("Protocol differs from existing output; choose a new output directory")
    save(path, manifest)


def read_rows(path):
    return (
        [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if path.exists()
        else []
    )


def campaign(args, model, digest, transport):
    cfg = Config(llm_agents=(0, 2, 4), llm_model=model)
    output = args.output / model.replace(":", "_")
    train_seeds = list(range(args.train_start, args.train_start + args.train_seeds))
    eval_seeds = list(range(args.eval_start, args.eval_start + args.eval_seeds))
    root = Path(__file__).resolve().parents[1]
    source_files = sorted((root / "src/mica_comm").rglob("*.py")) + [
        Path(__file__).resolve(),
        root / "experiments/run_etom_calibration.py",
    ]
    source_digest = hashlib.sha256(b"".join(p.read_bytes() for p in source_files)).hexdigest()
    manifest = {
        "protocol": 1,
        "source_sha256": source_digest,
        "model": model,
        "model_digest": digest,
        "config": json.loads(json.dumps(asdict(cfg))),
        "generation": {
            "think": False,
            "temperature": 0,
            "seed": 0,
            "num_predict": 12,
            "num_ctx": 1024,
        },
        "grid": PARAMETERS,
        "train_seeds": train_seeds,
        "eval_seeds": eval_seeds,
        "sample_interval": args.sample_interval,
        "scenarios": args.scenarios,
    }
    manifest = json.loads(json.dumps(manifest))
    check_manifest(output / "manifest.json", manifest)
    client = LLMClient(model, cache_dir=str(output / "cache"), transport=transport)
    llm_agent._CLIENTS[model] = client
    if client.choose("Return JSON with choice A.", ["A"]) != "A":
        raise RuntimeError(f"Warmup failed for {model}")
    training_path = output / "training.jsonl"
    training = read_rows(training_path)
    done = {r["seed"] for r in training}
    with training_path.open("a", encoding="utf-8") as stream:
        for seed in train_seeds:
            if seed in done:
                continue
            row = mission(cfg, seed, client, transport, args.sample_interval, collect=True)
            training.append(row)
            stream.write(json.dumps(row) + "\n")
            stream.flush()
            print(
                f"{model} train {len(training)}/{len(train_seeds)}: slots={row['completion_time']} calls={row['inference']['cache_misses']}",
                flush=True,
            )
    selected = {k: v for k, v in fit(training).items() if k in ("baseline", "calibrated")}
    calibration = {
        v: {"indices": ids, "parameters": [PARAMETERS[i] for i in ids]}
        for v, ids in selected.items()
    }
    save(output / "calibration.json", calibration)
    print(f"{model} frozen calibration: {json.dumps(calibration)}", flush=True)
    rows_path = output / "missions.jsonl"
    rows = read_rows(rows_path)
    done = {(r["scenario"], r["variant"], r["seed"]) for r in rows}
    with rows_path.open("a", encoding="utf-8") as stream:
        for scenario in args.scenarios:
            for seed in eval_seeds:
                # Alternate arm order to reduce systematic execution-order effects.
                variants = (
                    ("baseline", "calibrated") if seed % 2 == 0 else ("calibrated", "baseline")
                )
                for variant in variants:
                    if (scenario, variant, seed) in done:
                        continue
                    overrides = dict(SCENARIOS[scenario])
                    if variant == "calibrated":
                        overrides.update(
                            etom_receiver_temperatures=tuple(PARAMETERS[i][0] for i in selected[variant]),
                            etom_intent_persistences=tuple(PARAMETERS[i][1] for i in selected[variant]),
                        )
                    row = mission(
                        cfg.with_(**overrides),
                        seed,
                        client,
                        transport,
                        args.sample_interval,
                        collect=variant == "baseline",
                    )
                    row.update(scenario=scenario, variant=variant)
                    rows.append(row)
                    stream.write(json.dumps(row) + "\n")
                    stream.flush()
                    print(
                        f"{model} eval {len(rows)}/{2 * len(eval_seeds) * len(args.scenarios)}: {scenario} {variant} seed={seed} slots={row['completion_time']} symbols={row['symbols']} calls={row['inference']['cache_misses']}",
                        flush=True,
                    )
    report = {
        "manifest": manifest,
        "calibration": calibration,
        "results": summarize(rows, selected, cfg.llm_agents),
    }
    save(output / "summary.json", report)
    print(json.dumps({model: report["results"]}, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=["qwen3:8b", "llama3.1:8b"])
    parser.add_argument("--train-seeds", type=int, default=8)
    parser.add_argument("--eval-seeds", type=int, default=12)
    parser.add_argument("--train-start", type=int, default=6000)
    parser.add_argument("--eval-start", type=int, default=7000)
    parser.add_argument("--sample-interval", type=int, default=5)
    parser.add_argument(
        "--scenarios", nargs="+", choices=SCENARIOS, default=["default", "clustered"]
    )
    parser.add_argument("--output", type=Path, default=RESULTS_DIR / "llm_behavior_calibration")
    parser.add_argument(
        "--url", default="http://127.0.0.1:11434", help="Ollama base URL (omit /api/generate)"
    )
    parser.add_argument(
        "--windows-python", help="WSL path to Windows python.exe for localhost interop"
    )
    args = parser.parse_args()
    if min(args.train_seeds, args.eval_seeds, args.sample_interval) <= 0:
        parser.error("seed counts and sample interval must be positive")
    if set(range(args.train_start, args.train_start + args.train_seeds)) & set(
        range(args.eval_start, args.eval_start + args.eval_seeds)
    ):
        parser.error("training and evaluation seeds must be disjoint")
    transport = OllamaTransport(args.url, args.windows_python)
    try:
        models = {m["name"]: m["digest"] for m in transport.request("/api/tags")["models"]}
        for model in args.models:
            if model not in models:
                parser.error(f"Model not installed: {model}")
        for model in args.models:
            campaign(args, model, models[model], transport)
    finally:
        transport.close()


if __name__ == "__main__":
    main()
