"""Read a complete campaign without silently mixing seeds or configurations."""

import json
from pathlib import Path


def load_current(root):
    """Require exactly the manifest's configuration-by-seed product.

    Failed missions remain in the cohort. Missing, duplicated, or mismatched
    records are errors rather than grounds for dropping observations.
    """
    root = Path(root)
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (root / "missions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    seeds = manifest["seeds"]
    if len(set(seeds)) != len(seeds) or len(seeds) < 2:
        raise ValueError("Campaign needs at least two distinct mission seeds")
    cells = {
        (c["experiment"], c["parameter"], c["scheme"]): c["config"] for c in manifest["design"]
    }
    expected = {(*cell, seed) for cell in cells for seed in seeds}
    seen = set()
    for row in rows:
        cell = row["experiment"], row["parameter"], row["scheme"]
        key = *cell, row["seed"]
        if key not in expected or key in seen or row["config"] != cells[cell]:
            raise ValueError("Unexpected, duplicated or incompatible mission record")
        seen.add(key)
    if seen != expected or len(rows) != manifest["expected_rows"]:
        raise ValueError("Incomplete campaign")
    return rows, manifest
