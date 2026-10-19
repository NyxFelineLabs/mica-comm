"""Import experiment records for plotting while preserving their provenance.

Method IDs are preserved unless an explicit mapping is supplied. Importing
records does not run experiments or generate new measurements.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Dict, Optional

BASELINE = ("agents", "budget", "default", "pareto", "pareto_tv", "snr", "trajectories")
REALISTIC = ("theory", "validate_noise", "validate_overhead", "validate_shared")


def translate(value, aliases: Optional[Dict[str, str]] = None):
    """Rename configured method tokens while preserving values and other text."""
    aliases = aliases or {}
    if isinstance(value, str):
        if not aliases:
            return value
        tokens = "|".join(re.escape(token) for token in sorted(aliases, key=len, reverse=True))
        # A single pass prevents mappings from being reapplied to their own output.
        return re.sub(
            rf"(?<![A-Za-z0-9])(?:{tokens})(?=$|[^A-Za-z0-9])",
            lambda match: aliases[match.group(0)],
            value,
        )
    if isinstance(value, list):
        return [translate(item, aliases) for item in value]
    if isinstance(value, dict):
        result = {translate(key, aliases): translate(item, aliases) for key, item in value.items()}
        if len(result) != len(value):
            raise ValueError("Method translation would merge source keys")
        return result
    return value


def import_results(source, output, aliases=None):
    """Import a complete figure dataset with optional, recorded method aliases."""
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
        "origin": "Existing archived experiment records supplied for figure restoration",
        "fresh_inference": False,
        "method_aliases": aliases or {},
        "changes": "rev_ filenames become robustness_; configured method aliases are applied; numeric observations unchanged",
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
                    outgoing.write(json.dumps(translate(json.loads(line), aliases)) + "\n")
                    count += 1
        else:
            original = json.loads(path.read_text(encoding="utf-8"))
            target.write_text(json.dumps(translate(original, aliases)) + "\n", encoding="utf-8")
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
    parser.add_argument(
        "--rename-method",
        action="append",
        default=[],
        metavar="SOURCE=TARGET",
        help="Rename a method token; may be provided more than once.",
    )
    args = parser.parse_args()
    aliases = {}
    for entry in args.rename_method:
        source, separator, target = entry.partition("=")
        if not separator or not source or not target:
            parser.error(f"invalid method mapping {entry!r}; expected SOURCE=TARGET")
        aliases[source] = target
    import_results(args.source, args.output, aliases)


if __name__ == "__main__":
    main()
