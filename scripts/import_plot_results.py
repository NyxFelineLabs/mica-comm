"""Import historical experiment data for figure restoration, preserving provenance.

This translates method IDs and filenames only. It does not run experiments,
change observations, import response caches or claim fresh MICA measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

BASELINE = ("agents", "budget", "default", "pareto", "pareto_tv", "snr", "trajectories")
REALISTIC = ("theory", "validate_noise", "validate_overhead", "validate_shared")


def translate(value):
    """Translate a historical method token while preserving every numeric value."""
    if isinstance(value, str):
        return re.sub(r"(?<![A-Za-z0-9])gosc(?=$|[^A-Za-z0-9])", "mica", value)
    if isinstance(value, list):
        return [translate(item) for item in value]
    if isinstance(value, dict):
        result = {translate(key): translate(item) for key, item in value.items()}
        if len(result) != len(value):
            raise ValueError("Method translation would merge source keys")
        return result
    return value


def import_results(source, output):
    source, output = Path(source).resolve(), Path(output).resolve()
    if source == output or source in output.parents:
        raise ValueError("Import output must be outside the source data directory")
    selected = [source / f"{name}.json" for name in (*BASELINE, *REALISTIC)]
    selected += sorted(source.glob("rev_*.json"))
    selected += [source / f"{name}.jsonl" for name in ("noise", "overhead", "shared")]
    missing = [p.name for p in selected if not p.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing source files: {missing}")
    targets = [output / path.name.replace("rev_", "robustness_", 1) for path in selected]
    existing = [path.name for path in [*targets, output / "provenance.json"] if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite imported data: {existing}")
    output.mkdir(parents=True, exist_ok=True)
    manifest = {
        "kind": "historical-figure-restoration",
        "origin": "Existing experiment records accompanying the reference figure suite",
        "fresh_inference": False,
        "changes": "rev_ filenames become robustness_; method token translated to mica; numeric observations unchanged",
        "files": [],
    }
    for path, target in zip(selected, targets):
        count = None
        if path.suffix == ".jsonl":
            count = 0
            with (
                path.open(encoding="utf-8") as incoming,
                target.open("w", encoding="utf-8") as outgoing,
            ):
                for line in incoming:
                    if not line.strip():
                        continue
                    outgoing.write(json.dumps(translate(json.loads(line))) + "\n")
                    count += 1
        else:
            original = json.loads(path.read_text(encoding="utf-8"))
            target.write_text(json.dumps(translate(original)) + "\n", encoding="utf-8")
            if isinstance(original, dict) and "rows" in original:
                count = len(original["rows"])
        manifest["files"].append(
            {
                "source_name": path.name,
                "imported_name": target.name,
                "records": count,
                "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "imported_sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            }
        )
    (output / "provenance.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Imported {len(selected)} files; observations preserved; no experiments run")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    import_results(args.source, args.output)


if __name__ == "__main__":
    main()
