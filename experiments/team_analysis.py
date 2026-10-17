"""Validate benchmark cells and compare models using matched mission seeds."""

from __future__ import annotations

import csv
import hashlib
import json
from itertools import combinations
from pathlib import Path

import numpy as np

from experiments.run_team_benchmark import MODELS, POLICIES

MODEL_LABELS = {
    "qwen3:8b": "Qwen3 8B",
    "llama3.1:8b": "Llama 3.1 8B",
    "gemma3:12b": "Gemma 3 12B",
}
BOOTSTRAP_SEED = 5821
N_BOOTSTRAP = 10000
SOURCE_FIELDS = (
    "model",
    "scenario",
    "scheme",
    "seed",
    "completion_time",
    "symbols",
    "completed",
    "llm_fallbacks",
)


def mean_interval(values):
    """Mean and exploratory 95% percentile CI, resampling entire missions.

    Each call resets the generator so the result is independent of plot order.
    Pass within-seed differences to preserve pairing for a model contrast.
    A singleton has no estimable mission variability and is rejected.
    """
    values = np.asarray(values, dtype=float)
    if values.ndim != 1 or len(values) < 2 or not np.isfinite(values).all():
        raise ValueError("Intervals require at least two finite mission values")
    indices = np.random.default_rng(BOOTSTRAP_SEED).integers(
        0, len(values), (N_BOOTSTRAP, len(values))
    )
    low, high = np.percentile(values[indices].mean(axis=1), [2.5, 97.5])
    return {"mean": float(values.mean()), "low": float(low), "high": float(high)}


def _index(rows):
    indexed = {}
    for row in rows:
        key = (row["model"], row["scenario"], row["scheme"], row["seed"])
        if key in indexed:
            raise ValueError(f"Duplicate benchmark cell: {key}")
        indexed[key] = row
    return indexed


def validate_campaign(rows, manifests):
    """Require the full scheduled cohort and comparable settings across models.

    Completed=False records remain valid. A backend fallback, missing cell,
    extra cell or incompatible run configuration invalidates the comparison.
    """
    if len(manifests) < 2:
        raise ValueError("Model comparison requires at least two models")
    indexed = _index(rows)
    expected = set()
    reference = None
    for model, manifest in manifests.items():
        if manifest["model"] != model:
            raise ValueError("Manifest model mismatch")
        seeds = manifest["seeds"]
        scenarios = manifest["scenarios"]
        policies = manifest["policies"]
        if (
            len(seeds) < 2
            or len(set(seeds)) != len(seeds)
            or len(set(scenarios)) != len(scenarios)
            or len(policies) != len(POLICIES)
            or set(policies) != set(POLICIES)
        ):
            raise ValueError("Invalid scheduled seeds, scenarios or policies")
        config = {k: v for k, v in manifest["config"].items() if k != "llm_model"}
        signature = {
            "protocol": manifest["protocol"],
            "source_sha256": manifest["source_sha256"],
            "generation": manifest["generation"],
            "ollama_version": manifest["ollama_version"],
            "config": config,
            "seeds": sorted(seeds),
            "scenarios": sorted(scenarios),
        }
        if reference is not None and signature != reference:
            raise ValueError("Incompatible manifests: settings or seed cohorts differ")
        reference = signature
        expected.update(
            (model, scene, policy, seed)
            for scene in scenarios
            for policy in policies
            for seed in seeds
        )
    if set(indexed) != expected:
        raise ValueError(
            f"Incomplete cohort: missing={len(expected - set(indexed))}, extra={len(set(indexed) - expected)}"
        )
    for row in rows:
        if row["llm_fallbacks"]:
            raise ValueError("Benchmark contains model-backend fallbacks")
        for metric in ("completion_time", "symbols"):
            value = row[metric]
            if not np.isfinite(value) or value < 0:
                raise ValueError(f"Invalid {metric} in benchmark")
    return indexed


def load_campaign(root):
    """Read original JSONL runs or our compact, public CSV snapshot."""
    root = Path(root)
    manifests = {
        model: json.loads(
            (root / model.replace(":", "_") / "manifest.json").read_text(encoding="utf-8")
        )
        for model in MODELS
    }
    source_csv = root / "missions.csv"
    if source_csv.exists():
        with source_csv.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        for row in rows:
            for key in ("seed", "completion_time", "symbols", "llm_fallbacks"):
                row[key] = int(row[key])
            if row["completed"] not in {"True", "False"}:
                raise ValueError("Invalid completion status in source CSV")
            row["completed"] = row["completed"] == "True"
    else:
        rows = []
        for model in MODELS:
            path = root / model.replace(":", "_") / "missions.jsonl"
            rows.extend(
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            )
    validate_campaign(rows, manifests)
    return rows, manifests


def write_source_csv(rows, path):
    """Publish mission outcomes without prompts, response caches or timings."""
    with Path(path).open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=SOURCE_FIELDS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(
            sorted(rows, key=lambda r: (r["model"], r["scenario"], r["scheme"], r["seed"]))
        )


def analyze(rows, manifests, scenario="default"):
    """Return absolute outcomes and all within-seed, cross-model contrasts."""
    indexed = validate_campaign(rows, manifests)
    first = next(iter(manifests.values()))
    if scenario not in first["scenarios"]:
        raise ValueError(f"Scenario not scheduled: {scenario}")
    seeds = sorted(first["seeds"])
    models = list(manifests)
    absolute = {}
    for model in models:
        absolute[model] = {}
        for policy in POLICIES:
            group = [indexed[model, scenario, policy, seed] for seed in seeds]
            absolute[model][policy] = {
                "n": len(group),
                "completion_rate": float(np.mean([r["completed"] for r in group])),
                "completion_time": mean_interval([r["completion_time"] for r in group]),
                "symbols": (
                    None if policy == "genie" else mean_interval([r["symbols"] for r in group])
                ),
            }
    contrasts = []
    for first_model, second_model in combinations(models, 2):
        for policy in POLICIES:
            differences = [
                indexed[first_model, scenario, policy, seed]["completion_time"]
                - indexed[second_model, scenario, policy, seed]["completion_time"]
                for seed in seeds
            ]
            contrasts.append(
                {
                    "first": first_model,
                    "second": second_model,
                    "policy": policy,
                    "differences": differences,
                    **mean_interval(differences),
                }
            )
    canonical = json.dumps(
        [
            {key: row[key] for key in SOURCE_FIELDS}
            for row in sorted(
                rows, key=lambda r: (r["model"], r["scenario"], r["scheme"], r["seed"])
            )
        ],
        sort_keys=True,
    )
    return {
        "scenario": scenario,
        "seeds": seeds,
        "rows_total": len(rows),
        "rows_selected": sum(r["scenario"] == scenario for r in rows),
        "selection": "All models and policies; only the explicitly selected scenario is plotted",
        "statistics": {
            "unit": "mission seed",
            "interval": "95% percentile bootstrap",
            "resamples": N_BOOTSTRAP,
            "seed": BOOTSTRAP_SEED,
            "multiplicity": "Unadjusted, exploratory",
        },
        "input_records_sha256": hashlib.sha256(canonical.encode()).hexdigest(),
        "absolute": absolute,
        "contrasts": contrasts,
    }
