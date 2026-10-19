"""Core simulation, communication, and belief-accounting invariants."""

import itertools

import numpy as np
import pytest

from mica_comm import Config, Simulation, run_episode
from mica_comm.communication.channel import Channel
from mica_comm.communication.messages import evidence_bits, evidence_sizes
from mica_comm.communication.schemes import (
    SCHEMES,
    Group,
    Option,
    exact_select,
)
from mica_comm.world.belief import Obs, SensorModel, box_sum, logit


def test_unknown_scheme_error_lists_available_choices():
    with pytest.raises(ValueError, match="Unknown scheme"):
        Simulation(Config(), "does-not-exist", seed=0)


def test_box_sum_matches_bruteforce():
    rng = np.random.default_rng(0)
    a = rng.random((9, 9))
    r = 2
    got = box_sum(a, r)
    for i in range(9):
        for j in range(9):
            ref = a[max(i - r, 0) : i + r + 1, max(j - r, 0) : j + r + 1].sum()
            assert got[i, j] == pytest.approx(ref)


def test_sensor_apply_is_reversible():
    s = SensorModel(0.85, 0.05, 2, 16)
    L = np.full((16, 16), logit(0.01))
    ref = L.copy()
    rec = Obs(0, 0, (0, 3), (1 * 16 + 4,))
    s.apply(L, rec)
    assert L[1, 4] == pytest.approx(ref[1, 4] + s.llr_pos)
    assert L[0, 1] == pytest.approx(ref[0, 1] + s.llr_neg)
    assert L[0, 0] == ref[0, 0]  # outside the footprint
    s.apply(L, rec, sign=-1.0)
    assert np.allclose(L, ref)


def test_outage_probability_matches_monte_carlo():
    rng = np.random.default_rng(1)
    snr, rate = 4.0, 1.5
    g = rng.exponential(size=200_000)
    mc = np.mean(np.log2(1 + snr * g) >= rate)
    assert Channel(Config(), (16, 16)).success_prob(rate, snr) == pytest.approx(mc, abs=5e-3)


def test_fixed_rate_meets_bler_target():
    cfg = Config()
    ch = Channel(cfg, (16, 16))
    for snr_db in (-5, 0, 10, 20):
        snr = 10 ** (snr_db / 10)
        r = ch.fixed_rate(snr)
        if r > min(cfg.rates):
            assert 1 - ch.success_prob(r, snr) <= cfg.target_bler + 1e-12


def test_evidence_sizes_monotone_and_jump_cost():
    cfg = Config()
    recs = [Obs(t, 0, (5, 5), ()) for t in (0, 1, 2, 7)]
    sizes = evidence_sizes(recs, cfg)
    assert sizes == sorted(sizes)
    assert sizes[-1] == evidence_bits(4, 0, cfg, n_jumps=1)


def test_exact_scheduler_matches_enumeration():
    rng = np.random.default_rng(7)
    for _ in range(100):
        groups = [
            Group(
                str(i),
                [
                    Option(1.0, 1, int(rng.integers(1, 12)), float(rng.random() * 2))
                    for _ in range(int(rng.integers(1, 4)))
                ],
            )
            for i in range(int(rng.integers(0, 5)))
        ]
        budget = int(rng.integers(0, 20))
        price = float(rng.random() / 10)
        chosen = exact_select(groups, budget, price)
        got = sum(o.value - price * o.symbols for _, o in chosen)
        expected = max(
            sum(o.value - price * o.symbols for o in combo if o is not None)
            for combo in itertools.product(*[[None] + g.options for g in groups])
            if sum(o.symbols for o in combo if o is not None) <= budget
        )
        assert got == pytest.approx(expected)
        assert sum(o.symbols for _, o in chosen) <= budget


def test_mica_transmit_uses_exact_scheduler(monkeypatch):
    sim = Simulation(Config(), "mica", seed=0)
    agent = sim.agents[0]
    groups = [
        Group("CONF", [Option(1.0, 1, 60, 10.0)]),
        Group("INTENT", [Option(1.0, 1, 50, 9.0)]),
        Group("EVID", [Option(1.0, 1, 50, 9.0)]),
    ]
    monkeypatch.setattr(sim.scheme, "build_groups", lambda *args: groups)
    monkeypatch.setattr(sim.channel, "decodes", lambda *args, **kwargs: False)
    result = sim.scheme.transmit(agent, 0, 1.0, 1.0, sim)
    assert result.symbols == 100
    assert sum(o.value for _, o in exact_select(groups, 100, 0.0)) == 18.0


@pytest.mark.parametrize("scheme", sorted(SCHEMES))
def test_belief_bookkeeping_invariant(scheme):
    """Edge belief = prior + all delivered evidence, and each agent's pending map =
    its own evidence minus what it got delivered (so local = shared + own pending)."""
    cfg = Config().with_(max_steps=40, n_agents=3)
    sim = Simulation(cfg, scheme, seed=3)
    own = {a.idx: [] for a in sim.agents}
    delivered = {a.idx: [] for a in sim.agents}
    orig_step, orig_deliver = sim.scheme.on_step, sim.deliver

    def spy_step(agent, rec, t, s):
        own[agent.idx].append(rec)
        return orig_step(agent, rec, t, s)

    def spy_deliver(agent, pkt, t):
        delivered[agent.idx].extend(pkt.records)
        return orig_deliver(agent, pkt, t)

    sim.scheme.on_step, sim.deliver = spy_step, spy_deliver
    sim.run()
    lc = np.full_like(sim.Lc, sim.prior)
    for k in delivered:
        for rec in delivered[k]:
            sim.sensor.apply(lc, rec)
    np.testing.assert_allclose(sim.Lc, lc, atol=1e-8)
    for a in sim.agents:
        pend = np.zeros_like(sim.Lc)
        for rec in own[a.idx]:
            sim.sensor.apply(pend, rec)
        for rec in delivered[a.idx]:
            sim.sensor.apply(pend, rec, sign=-1.0)
        np.testing.assert_allclose(a.pending_llr, pend, atol=1e-8)
        assert all(r.agent == a.idx for r in delivered[a.idx])


def test_genie_delivers_everything():
    cfg = Config().with_(max_steps=30)
    sim = Simulation(cfg, "genie", seed=0)
    sim.run()
    for a in sim.agents:
        assert np.allclose(a.pending_llr, 0.0, atol=1e-8)


def test_episode_is_deterministic():
    cfg = Config().with_(max_steps=80)
    assert run_episode(cfg, "mica", 5) == run_episode(cfg, "mica", 5)


def test_all_schemes_complete_easy_mission():
    cfg = Config().with_(n_victims=2, snr_ref_db=20)
    for s in SCHEMES:
        out = run_episode(cfg, s, 0)
        assert out["found"] == 2, s
