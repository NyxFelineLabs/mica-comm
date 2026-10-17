"""Keep aggregate comparisons paired and include unsuccessful missions."""

import pytest

from experiments.run_team_benchmark import summarize


def record(scheme, seed, slots, symbols, completed=True):
    return {
        "scheme": scheme,
        "seed": seed,
        "scenario": "default",
        "completion_time": slots,
        "symbols": symbols,
        "bits": 10,
        "completed": completed,
        "llm_decisions": 2,
        "llm_fallbacks": 0,
        "elapsed_seconds": 1.0,
        "inference": {"http_requests": 1, "cache_hits": 1},
    }


def test_summary_pairs_by_seed_and_includes_capped_failure():
    rows = [
        record("mica", 2, 400, 80, completed=False),
        record("sem", 1, 50, 100),
        record("genie", 1, 30, 0),
        record("mica", 1, 40, 80),
        record("sem", 2, 100, 200),
        record("genie", 2, 40, 0),
    ]
    mica = summarize(rows)["default"]["mica"]
    assert mica["completion_rate"] == 0.5
    assert mica["completion_slots"] == 220
    assert mica["uplink_symbols"] == 80
    assert mica["slot_difference_vs_sem"]["mean"] == 145
    assert mica["symbol_difference_vs_sem"]["mean"] == -70
    assert mica["llm_decisions"] == 4
    assert mica["inference"] == {"http_requests": 2, "cache_hits": 2}


def test_summary_rejects_missing_paired_periodic_seed():
    with pytest.raises(ValueError, match="matching periodic seeds"):
        summarize([record("mica", 2, 40, 80), record("sem", 1, 50, 100)])
