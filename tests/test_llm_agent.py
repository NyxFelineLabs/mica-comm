import json

import pytest

from mica_comm import Config, Simulation, llm_agent
from mica_comm.agents.llm_agent import LLMAgent, LLMClient


def fake_transport(answer):
    calls = []

    def transport(body):
        calls.append(body)
        return {"response": json.dumps({"choice": answer}) if answer else "not json"}

    transport.calls = calls
    return transport


@pytest.fixture
def client_factory(tmp_path, monkeypatch):
    def make(answer):
        tr = fake_transport(answer)
        c = LLMClient("fake-model", cache_dir=str(tmp_path), transport=tr)
        monkeypatch.setitem(llm_agent._CLIENTS, "fake-model", c)
        return c, tr

    monkeypatch.setattr(llm_agent.time, "sleep", lambda s: None)
    return make


def test_mixed_team_runs_and_uses_schema(client_factory):
    client, tr = client_factory("A")
    cfg = Config().with_(llm_agents=(0, 2), llm_model="fake-model", max_steps=40)
    sim = Simulation(cfg, "mica", seed=1)
    out = sim.run()
    assert isinstance(sim.agents[0], LLMAgent) and not isinstance(sim.agents[1], LLMAgent)
    assert out["llm_decisions"] > 0 and out["llm_fallbacks"] == 0
    body = tr.calls[0]
    assert body["format"]["properties"]["choice"]["enum"][0] == "A"
    assert body["options"]["temperature"] == 0


def test_cache_makes_runs_deterministic_without_model(client_factory, tmp_path):
    client, tr = client_factory("B")
    cfg = Config().with_(llm_agents=(1,), llm_model="fake-model", max_steps=30)
    first = Simulation(cfg, "sem", seed=2).run()
    n_calls = len(tr.calls)
    # a fresh client that would fail on any call must reproduce the run from cache
    offline = LLMClient(
        "fake-model",
        cache_dir=str(tmp_path),
        transport=lambda b: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    llm_agent._CLIENTS["fake-model"] = offline
    second = Simulation(cfg, "sem", seed=2).run()
    assert n_calls > 0 and offline.calls == 0
    assert first == second


def test_invalid_output_falls_back_to_planner(client_factory):
    client_factory(None)
    cfg = Config().with_(llm_agents=(0,), llm_model="fake-model", max_steps=15)
    out = Simulation(cfg, "mica", seed=0).run()
    assert out["llm_fallbacks"] == out["llm_decisions"] > 0


def test_three_models_are_used_by_the_scheduled_agents(tmp_path, monkeypatch):
    models = ("qwen-test", "llama-test", "gemma-test")
    for model, choice in zip(models, ("A", "B", "C")):
        client = LLMClient(model, cache_dir=str(tmp_path), transport=fake_transport(choice))
        monkeypatch.setitem(llm_agent._CLIENTS, model, client)
    cfg = Config(llm_agents=(0, 2, 4), llm_models=models, max_steps=10)
    sim = Simulation(cfg, "mica", seed=1)
    result = sim.run()
    assert [a.client.model for a in sim.agents if isinstance(a, LLMAgent)] == list(models)
    assert sum(isinstance(a, LLMAgent) for a in sim.agents) == 3
    assert result["llm_fallbacks"] == 0
    assert {k: v["model"] for k, v in result["llm_by_agent"].items()} == dict(
        zip(("0", "2", "4"), models)
    )
    assert all(v["decisions"] > 0 for v in result["llm_by_agent"].values())


@pytest.mark.parametrize(
    "kwargs",
    [
        {"llm_agents": (0, 2, 4), "llm_models": ("one",)},
        {"llm_agents": (0, 0)},
        {"llm_agents": (6,)},
        {"llm_agents": (-1,)},
    ],
)
def test_invalid_llm_assignment_rejected(kwargs):
    with pytest.raises(ValueError):
        Simulation(Config(**kwargs), "mica", 0)
