"""The figure pipeline must reject incomplete or incompatible experiments."""

import json

import pytest

from mica_comm.evaluation.campaign import load_current


def write_campaign(root, rows):
    config = {"grid": 8}
    manifest = {
        "seeds": [10, 11],
        "expected_rows": 2,
        "design": [{"experiment": "default", "parameter": 0, "scheme": "mica", "config": config}],
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (root / "missions.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
    )


@pytest.fixture
def records():
    return [
        {
            "experiment": "default",
            "parameter": 0,
            "scheme": "mica",
            "seed": seed,
            "config": {"grid": 8},
            "completed": False,
            "completion_time": 400,
        }
        for seed in (10, 11)
    ]


def test_failed_missions_are_kept(tmp_path, records):
    write_campaign(tmp_path, records)
    rows, _ = load_current(tmp_path)
    assert len(rows) == 2 and all(not row["completed"] for row in rows)


@pytest.mark.parametrize("problem", ("missing", "duplicate", "unknown_seed", "configuration"))
def test_incompatible_missions_rejected(tmp_path, records, problem):
    if problem == "missing":
        records.pop()
    elif problem == "duplicate":
        records[1] = records[0].copy()
    elif problem == "unknown_seed":
        records[1]["seed"] = 12
    else:
        records[1]["config"] = {"grid": 16}
    write_campaign(tmp_path, records)
    with pytest.raises(ValueError):
        load_current(tmp_path)
