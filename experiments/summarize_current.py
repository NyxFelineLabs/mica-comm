"""Validate a complete campaign and export paired results and a Table XII layout."""

import argparse
import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from experiments.team_analysis import mean_interval
from mica_comm.evaluation.campaign import load_current


def summarize(rows):
    groups = defaultdict(list)
    for row in rows:
        groups[row["experiment"], row["parameter"], row["scheme"]].append(row)
    results = []
    for (experiment, parameter, scheme), group in sorted(groups.items(), key=lambda x: str(x[0])):
        group.sort(key=lambda r: r["seed"])
        entry = {
            "experiment": experiment,
            "parameter": parameter,
            "scheme": scheme,
            "n": len(group),
            "completion_rate": float(np.mean([r["completed"] for r in group])),
            "llm_fallbacks": sum(r.get("llm_fallbacks", 0) for r in group),
            "llm_decisions": sum(r.get("llm_decisions", 0) for r in group),
        }
        for metric in ("completion_time", "symbols", "total_symbols", "saved_fraction"):
            if metric in group[0]:
                entry[metric] = mean_interval([r[metric] for r in group])
        if scheme == "mica" and (experiment, parameter, "sem") in groups:
            periodic = {r["seed"]: r for r in groups[experiment, parameter, "sem"]}
            if set(periodic) != {r["seed"] for r in group}:
                raise ValueError("Policy comparison requires identical seed cohorts")
            entry["periodic_minus_mica_slots"] = mean_interval(
                [periodic[r["seed"]]["completion_time"] - r["completion_time"] for r in group]
            )
            sem = np.array([periodic[r["seed"]]["symbols"] for r in group], dtype=float)
            mica = np.array([r["symbols"] for r in group], dtype=float)
            indices = np.random.default_rng(5821).integers(0, len(group), (10000, len(group)))
            ratios = sem[indices].mean(axis=1) / mica[indices].mean(axis=1)
            low, high = np.percentile(ratios, [2.5, 97.5])
            entry["periodic_over_mica_uplink"] = {
                "mean": float(sem.mean() / mica.mean()),
                "low": float(low),
                "high": float(high),
            }
        results.append(entry)
    return results


def write_report(root):
    root = Path(root)
    rows, manifest = load_current(root)
    results = summarize(rows)
    report = {
        "protocol": manifest["protocol"],
        "source_sha256": manifest["source_sha256"],
        "team": manifest.get("team", "planner"),
        "llm_agents": manifest.get("llm_agents", []),
        "llm_models": manifest.get("llm_models", []),
        "missions": len(rows),
        "expected_missions": manifest["expected_rows"],
        "llm_fallbacks": sum(r.get("llm_fallbacks", 0) for r in rows),
        "statistics": "95% percentile bootstrap over paired mission seeds, 10000 resamples; exploratory",
        "results": results,
        "report_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inference": {
            metric: sum(row.get("inference", {}).get(metric, 0) for row in rows)
            for metric in ("http_requests", "server_seconds", "prompt_tokens", "generated_tokens")
        },
    }
    report["llm_by_agent"] = {
        agent: {
            "model": rows[0]["llm_by_agent"][agent]["model"],
            **{
                metric: sum(row["llm_by_agent"][agent][metric] for row in rows)
                for metric in ("decisions", "fallbacks", "agree_with_planner")
            },
        }
        for agent in rows[0].get("llm_by_agent", {})
    }
    (root / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    fields = [
        "experiment",
        "parameter",
        "scheme",
        "seed",
        "completion_time",
        "completed",
        "symbols",
        "total_symbols",
        "saved_fraction",
        "llm_decisions",
        "llm_fallbacks",
    ]
    with (root / "metrics.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            sorted(
                rows, key=lambda r: str((r["experiment"], r["parameter"], r["scheme"], r["seed"]))
            )
        )
    mixed = manifest.get("team") == "mixed"
    lines = [
        "# Three planners + three different LLMs" if mixed else "# Planner diagnostic campaign",
        "",
        f"Validated {len(rows)}/{manifest['expected_rows']} missions; backend fallbacks: {report['llm_fallbacks']}.",
        "",
        (
            "LLM agents 0 / 2 / 4 use Qwen3 8B / Llama 3.1 8B / Gemma 3 12B respectively."
            if mixed
            else "All agents use classical planners."
        ),
        "",
        "This extends Table XII to three different models in one team and uses the current EToM and exact DP scheduler. It does not reproduce the paper's original model tags or numerical results.",
        "",
        "Team-size sweeps retain three LLMs and vary the number of planners. Failed missions remain in the cohort at the simulation horizon. Time is measured in simulation slots.",
        "",
    ]
    for experiment in ("table_xii", "default"):
        selected = [r for r in results if r["experiment"] == experiment]
        if not selected:
            continue
        lines += [
            f"## {experiment}",
            "",
            (
                "Orthogonal uplinks, 100 symbols per agent per slot."
                if experiment == "table_xii"
                else "Shared 300-symbol uplink, static equal shares."
            ),
            "",
            "| Scheme | Missions | Time [95% CI] | Uplink symbols | Total symbols | Completion |",
            "| --- | ---: | --- | ---: | ---: | ---: |",
        ]
        for entry in selected:
            t = entry["completion_time"]
            lines.append(
                f"| {entry['scheme']} | {entry['n']} | {t['mean']:.2f} [{t['low']:.2f}, {t['high']:.2f}] | {entry['symbols']['mean']:.2f} | {entry['total_symbols']['mean']:.2f} | {entry['completion_rate']:.1%} |"
            )
        mica = next((r for r in selected if r["scheme"] == "mica"), None)
        if mica and "periodic_minus_mica_slots" in mica:
            delta, ratio = mica["periodic_minus_mica_slots"], mica["periodic_over_mica_uplink"]
            lines += [
                "",
                f"Paired periodic − MICA time: {delta['mean']:.2f} [{delta['low']:.2f}, {delta['high']:.2f}] slots. Positive means MICA is faster.",
                "",
                f"Periodic / MICA uplink symbols: {ratio['mean']:.2f} [{ratio['low']:.2f}, {ratio['high']:.2f}].",
                "",
            ]
    (root / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps({k: v for k, v in write_report(args.input).items() if k != "results"}, indent=2)
    )
