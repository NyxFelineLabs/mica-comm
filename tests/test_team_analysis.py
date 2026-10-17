"""Protect paired model inference and the public plotting source-data contract."""

import copy
import json

import pytest

from experiments.run_team_benchmark import MODELS, POLICIES
from experiments.team_analysis import analyze, load_campaign, validate_campaign, write_source_csv


@pytest.fixture
def campaign():
    manifests, rows = {}, []
    for model_index, model in enumerate(MODELS):
        manifests[model] = {
            "protocol": "test",
            "source_sha256": "same-source",
            "model": model,
            "model_digest": str(model_index),
            "ollama_version": "test",
            "config": {"llm_model": model, "max_steps": 400},
            "generation": {"think": False},
            "seeds": [1, 2],
            "scenarios": ["default"],
            "policies": list(POLICIES),
        }
        for policy in POLICIES:
            for seed in (1, 2):
                rows.append(
                    {
                        "model": model,
                        "scenario": "default",
                        "scheme": policy,
                        "seed": seed,
                        "completion_time": 20 * seed + 5 * model_index,
                        "symbols": 100 * seed,
                        "completed": True,
                        "llm_fallbacks": 0,
                        "extra_accounting": "ignored by compact snapshot",
                    }
                )
    return rows[::-1], manifests


def test_contrasts_pair_by_seed_and_ideal_cost_is_not_zero(campaign):
    rows, manifests = campaign
    report = analyze(rows, manifests)
    for contrast in report["contrasts"]:
        expected = -5 * (MODELS.index(contrast["second"]) - MODELS.index(contrast["first"]))
        assert contrast["differences"] == [expected, expected]
        assert contrast["mean"] == contrast["low"] == contrast["high"] == expected
    assert report["absolute"][MODELS[0]]["genie"]["symbols"] is None


def test_capped_failures_are_included(campaign):
    rows, manifests = campaign
    selected = next(
        r for r in rows if r["model"] == MODELS[0] and r["scheme"] == "mica" and r["seed"] == 2
    )
    selected.update(completion_time=400, completed=False)
    group = analyze(rows, manifests)["absolute"][MODELS[0]]["mica"]
    assert group["completion_time"]["mean"] == 210
    assert group["completion_rate"] == 0.5


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "fallback", "extra", "configuration"])
def test_incomparable_campaign_is_rejected(campaign, mutation):
    rows, manifests = copy.deepcopy(campaign)
    if mutation == "missing":
        rows.pop()
    elif mutation == "duplicate":
        rows.append(dict(rows[0]))
    elif mutation == "fallback":
        rows[0]["llm_fallbacks"] = 1
    elif mutation == "extra":
        rows.append(dict(rows[0], seed=999))
    else:
        manifests[MODELS[1]]["generation"]["think"] = True
    with pytest.raises(ValueError):
        validate_campaign(rows, manifests)


def test_compact_source_rebuild_matches_full_records(campaign, tmp_path):
    rows, manifests = campaign
    write_source_csv(rows, tmp_path / "missions.csv")
    for model, manifest in manifests.items():
        directory = tmp_path / model.replace(":", "_")
        directory.mkdir()
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    restored_rows, restored_manifests = load_campaign(tmp_path)
    assert analyze(restored_rows, restored_manifests) == analyze(rows, manifests)
