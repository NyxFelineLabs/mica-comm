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


def test_main_campaign_uses_three_different_models_in_every_cell():
    from experiments.run_current import MODELS, design

    cells = design()
    for experiment, _, _, cfg in cells:
        assert cfg.llm_agents == (0, 2, 4)
        assert cfg.llm_models == MODELS
        assert cfg.n_agents >= 6
        if experiment != "agents":
            assert cfg.n_agents == 6
    assert all(not cfg.llm_agents for _, _, _, cfg in design("planner"))


def test_backend_fallback_invalidates_campaign(tmp_path, records):
    records[0]["llm_fallbacks"] = 1
    write_campaign(tmp_path, records)
    with pytest.raises(ValueError, match="fallback"):
        load_current(tmp_path)


def test_three_model_team_cannot_be_replaced_by_one_model(tmp_path, records):
    write_campaign(tmp_path, records)
    path = tmp_path / "manifest.json"
    manifest = json.loads(path.read_text())
    manifest["team"] = "mixed"
    cfg = {"grid": 8, "llm_agents": [0, 2, 4], "llm_models": ["a", "b", "c"]}
    manifest["design"][0]["config"] = cfg
    path.write_text(json.dumps(manifest))
    for row in records:
        row["config"] = cfg
        row["llm_by_agent"] = {str(i): {"model": "a", "fallbacks": 0} for i in (0, 2, 4)}
    (tmp_path / "missions.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records))
    with pytest.raises(ValueError, match="scheduled LLM team"):
        load_current(tmp_path)


def test_workers_share_cached_responses_without_repeating_inference(tmp_path):
    import threading
    from concurrent.futures import ThreadPoolExecutor

    from experiments.run_current import CampaignLLMClient

    calls = []

    def transport(body):
        calls.append(body)
        return {"response": '{"choice":"A"}'}

    cache, lock = {}, threading.RLock()
    clients = [CampaignLLMClient("test", str(tmp_path), transport, cache, lock) for _ in range(2)]
    with ThreadPoolExecutor(2) as pool:
        answers = list(pool.map(lambda client: client.choose("same prompt", ["A", "B"]), clients))
    assert answers == ["A", "A"]
    assert len(calls) == 1
    assert sum(c.hits for c in clients) == 1
    assert len((tmp_path / "test.jsonl").read_text().splitlines()) == 1
