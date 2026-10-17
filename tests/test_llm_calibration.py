"""Guard the live-model experiment against silent planner substitution."""

import json

import pytest

from experiments.run_llm_calibration import OllamaTransport, check_manifest, mission
from mica_comm import Config, llm_agent, run_episode
from mica_comm.llm_agent import LLMClient


def setup_client(tmp_path, monkeypatch, answer):
    transport = OllamaTransport("http://unused")
    bodies = []

    def request(path, body):
        bodies.append(body)
        return {"response": json.dumps({"choice": answer}), "eval_count": 10}

    monkeypatch.setattr(transport, "request", request)
    monkeypatch.setattr(llm_agent.time, "sleep", lambda _: None)
    client = LLMClient("test-model", str(tmp_path), transport)
    monkeypatch.setitem(llm_agent._CLIENTS, "test-model", client)
    return client, transport, bodies


@pytest.mark.parametrize("scheme", ["sem", "mica", "genie"])
def test_instrumentation_preserves_mission(tmp_path, monkeypatch, scheme):
    client, transport, bodies = setup_client(tmp_path, monkeypatch, "A")
    cfg = Config(llm_agents=(0, 2, 4), llm_model="test-model", max_steps=12)
    expected = run_episode(cfg, scheme, 5)
    expected.pop("curve")
    measured = mission(cfg, 5, client, transport, interval=5, collect=True, scheme=scheme)
    assert {k: measured[k] for k in expected} == expected
    assert measured["samples_per_agent"] == 3
    assert measured["inference"]["cache_misses"] == 0
    assert measured["inference"]["cache_hits"] == measured["llm_decisions"] > 0
    assert bodies and all(body["think"] is False for body in bodies)


def test_live_validation_rejects_any_fallback(tmp_path, monkeypatch):
    client, transport, _ = setup_client(tmp_path, monkeypatch, "invalid")
    cfg = Config(llm_agents=(0,), llm_model="test-model", max_steps=12)
    with pytest.raises(RuntimeError, match="LLM fallback at seed 5, slot 0"):
        mission(cfg, 5, client, transport, interval=5)


def test_resume_rejects_changed_model_digest(tmp_path):
    path = tmp_path / "manifest.json"
    check_manifest(path, {"model_digest": "first"})
    check_manifest(path, {"model_digest": "first"})
    with pytest.raises(ValueError, match="Protocol differs"):
        check_manifest(path, {"model_digest": "replacement"})
