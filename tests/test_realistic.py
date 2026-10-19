"""The realistic-resource extensions must reproduce the base simulator exactly with
the default Config, and the new options must behave as specified."""

import pytest

from mica_comm import Config, run_episode, run_realistic
from mica_comm.communication.schemes import Option
from mica_comm.simulation.realistic import hull_size, waterfill

KEYS = ("completion_time", "symbols", "bits", "delivered_bits", "dl_symbols", "found")
SCHEMES = (
    "mica",
    "mica_bits",
    "sem",
    "sem_ra",
    "sem_raf",
    "sem_ras",
    "raw",
    "nl",
    "report",
    "genie",
)


@pytest.mark.parametrize("scheme", SCHEMES)
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_reproduces_base(scheme, seed):
    kw = dict(sem_interval=4, filter_eps=0.1) if scheme in ("sem_ra", "sem_raf", "sem_ras") else {}
    a = run_episode(Config().with_(**kw), scheme, seed)
    b = run_realistic(Config().with_(**kw), scheme, seed)
    assert {k: a[k] for k in KEYS} == {k: b[k] for k in KEYS}


@pytest.mark.parametrize("scheme", ("mica", "sem_ra"))
def test_reproduces_base_rescue_w50(scheme):
    kw = dict(task="rescue", deadline_min=60, deadline_max=180, symbols_per_slot=50)
    a = run_episode(Config().with_(**kw), scheme, 3)
    b = run_realistic(Config().with_(**kw), scheme, 3)
    assert a["saved_fraction"] == b["saved_fraction"] and a["symbols"] == b["symbols"]


def test_base_regression_episode():
    o = run_realistic(Config(), "mica", 0)
    assert (o["completion_time"], o["symbols"], o["bits"]) == (75, 14192, 16631)


def test_overhead_is_charged():
    base = run_realistic(Config(), "sem_ra", 0)
    oh = run_realistic(Config(overhead_bits=32), "sem_ra", 0)
    assert oh["ul_overhead_bits"] == 32 * oh["ul_tx"]
    g = run_realistic(Config(overhead_bits=32), "mica", 0)
    assert g["bits"] >= 32 * g["ul_tx"] and g["ul_tx"] > 0
    assert base["ul_overhead_bits"] == 0


def test_zero_noise_equals_exact():
    a = run_realistic(Config(), "mica", 1)
    b = run_realistic(Config(value_mode="lognormal", value_sigma=0.0), "mica", 1)
    assert a["completion_time"] == b["completion_time"] and a["symbols"] == b["symbols"]


def test_noise_changes_decisions_and_is_logged():
    o = run_realistic(Config(value_mode="lognormal", value_sigma=2.0), "mica", 1)
    assert "value_pairs" in o and len(o["value_pairs"]) > 10
    p = run_realistic(Config(value_mode="permuted"), "mica", 1)
    assert p["completed"]


@pytest.mark.parametrize(
    "scheme,mode",
    (("mica", "static"), ("mica", "price"), ("mica", "central"),
     ("sem_ra", "static"), ("sem_ra", "price")),
)
def test_shared_budget_respected(scheme, mode):
    from mica_comm.simulation.realistic import RealisticSimulation

    cfg = Config(shared_budget=150, symbols_per_slot=150, shared_mode=mode)
    sim = RealisticSimulation(cfg, scheme, 0)
    sim._start()
    last = 0
    for t in range(cfg.max_steps):
        sim.phase_decide(t)
        done = sim.phase_communicate(t)
        assert sim.symbols - last <= 150
        last = sim.symbols
        if done:
            break
    r = sim.result()
    if mode == "static":
        assert r["ul_ctrl_symbols"] == 0
    else:
        assert r["ul_ctrl_symbols"] > 0
    assert r["dl_ctrl_symbols"] > 0


def test_current_campaign_enables_shared_uplink():
    from experiments.run_current import design

    cells = design()
    assert all(cfg.shared_budget > 0 for _, _, _, cfg in cells)
    mica = next(cfg for experiment, _, scheme, cfg in cells if experiment == "default" and scheme == "mica")
    assert mica.shared_budget == 300 and mica.shared_mode == "static"
    rescue = next(
        cfg for experiment, _, scheme, cfg in cells if experiment == "rescue" and scheme == "mica"
    )
    assert rescue.shared_budget == 300 and rescue.shared_mode == "price"
    coordinator = {
        parameter: cfg.shared_mode
        for experiment, parameter, _, cfg in cells
        if experiment == "coordinator"
    }
    assert coordinator == {
        "search_static": "static",
        "search_price": "price",
        "search_central": "central",
        "rescue_static": "static",
        "rescue_price": "price",
        "rescue_central": "central",
    }
    budgets = [
        (parameter, cfg)
        for experiment, parameter, scheme, cfg in cells
        if experiment == "budget" and scheme == "mica"
    ]
    assert all(cfg.shared_budget // cfg.n_agents == parameter for parameter, cfg in budgets)
    assert all(
        cfg.shared_mode == "price"
        for experiment, _, _, cfg in cells
        if experiment == "shared"
    )


def test_static_share_matches_orthogonal_cap():
    static = run_realistic(Config(shared_budget=300, shared_mode="static"), "mica", 0)
    orthogonal = run_realistic(Config(symbols_per_slot=50), "mica", 0)
    assert {key: static[key] for key in KEYS} == {key: orthogonal[key] for key in KEYS}
    assert static["ul_ctrl_symbols"] == 0


def test_waterfill():
    assert waterfill([10, 0, 50, 50], 60, [1, 1, 1, 1]) == [10, 0, 25, 25]
    assert sum(waterfill([100, 100, 100], 100, [1, 1, 1])) == 100
    g = waterfill([100, 100], 100, [60, 1])
    assert g == [0, 100]


def test_hull_size():
    opts = [Option(1, 10, 10, 1.0), Option(2, 10, 5, 0.9), Option(4, 10, 3, 0.1)]
    assert hull_size(opts, 0.0) == 2
    assert hull_size(opts, 1.0) == 0
