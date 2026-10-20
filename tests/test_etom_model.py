"""Receiver calibration must preserve defaults and respect public information."""

import numpy as np
import pytest

from mica_comm import Config, Simulation
from mica_comm.agents.etom import EToMModel


def model(cfg):
    sim = Simulation(cfg, "mica", 0)
    sim.phase_decide(0)
    return sim, EToMModel(sim, sim.agents[0], cfg.etom_temperature)


def test_default_matches_explicit_identity_calibration():
    cfg = Config(n_agents=3)
    _, base = model(cfg)
    _, calibrated = model(
        cfg.with_(etom_receiver_temperatures=(0.2,) * 3, etom_intent_persistences=(2.0,) * 3)
    )
    for j in base.mates:
        expected = base._expected_utility(base.mass_shared, j, base.rep_known[j])
        actual = calibrated._expected_utility(calibrated.mass_shared, j, calibrated.rep_known[j])
        assert actual == expected


def test_persistence_uses_public_target_and_not_private_target():
    sim, team = model(Config(n_agents=3, etom_intent_persistences=(1000.0,) * 3))
    j = team.mates[0]
    target = int(np.argmax(team.u_true[j]))
    sim.team_intent[j] = target
    expected = team.u_true[j].reshape(-1)[target]
    actual = team._expected_utility(team.mass_shared, j, team.rep_known[j])
    assert actual == pytest.approx(expected)
    sim.agents[j].target = (target + 1) % (sim.cfg.grid**2)
    sim.agents[j].pending_llr[:] = 500.0
    rebuilt = EToMModel(sim, sim.agents[0], sim.cfg.etom_temperature)
    assert rebuilt._expected_utility(rebuilt.mass_shared, j, rebuilt.rep_known[j]) == actual


@pytest.mark.parametrize(
    "kwargs",
    [
        {"etom_receiver_temperatures": (0.2,)},
        {"etom_receiver_temperatures": (0.2, 0.0, 0.2)},
        {"etom_intent_persistences": (0.0, float("nan"), 0.0)},
    ],
)
def test_invalid_calibration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        model(Config(n_agents=3, **kwargs))
