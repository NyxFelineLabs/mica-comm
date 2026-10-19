"""Behavioral checks for the non-ToM task-weighted information gain module."""

import numpy as np

from mica_comm import Config, Simulation
from mica_comm.agents.information_gain import (
    InformationGainModel,
    TaskRelevanceModel,
    bernoulli_kl_from_logits,
)


def test_information_gain_is_zero_for_unchanged_belief():
    sim = Simulation(Config(n_agents=3), "mica_twig", 0)
    sim.phase_decide(0)
    model = InformationGainModel(sim, sim.agents[0])
    zero = np.zeros_like(sim.Lc)
    assert model.evidence_voi([zero], [sim.agents[0].pos]) == [0.0]


def test_information_gain_is_nonnegative_and_symmetric_in_surprise():
    p = np.full((3, 3), -2.0)
    positive = np.full((3, 3), 1.0)
    negative = np.full((3, 3), -5.0)
    assert np.all(bernoulli_kl_from_logits(p, positive) >= 0)
    assert np.all(bernoulli_kl_from_logits(p, negative) >= 0)
    assert float(bernoulli_kl_from_logits(p, positive).sum()) > 0
    assert float(bernoulli_kl_from_logits(p, negative).sum()) > 0


def test_twig_does_not_depend_on_private_receiver_state():
    sim = Simulation(Config(n_agents=3), "mica_twig", 7)
    sim.phase_decide(0)
    sender = sim.agents[0]
    model = InformationGainModel(sim, sender)
    delta = np.zeros_like(sim.Lc)
    delta[4, 4] = 3.0
    before = model.evidence_voi([delta], [sender.pos])[0]
    sim.agents[1].pending_llr[:] = 500.0
    sim.agents[1].target = 1
    after = InformationGainModel(sim, sender).evidence_voi([delta], [sender.pos])[0]
    assert after == before


def test_twig_and_ig_are_registered_in_both_simulators():
    from mica_comm.simulation.realistic import RealisticSimulation

    for scheme, cls in (
        ("mica_twig", Simulation),
        ("mica_ig", Simulation),
        ("mica_ptr", Simulation),
    ):
        base = cls(Config(max_steps=200), scheme, 1).run()
        realistic = RealisticSimulation(Config(max_steps=200), scheme, 1).run()
        assert base["completed"] and realistic["completed"]
        assert (base["completion_time"], base["symbols"]) == (
            realistic["completion_time"],
            realistic["symbols"],
        )


def test_public_task_relevance_uses_footprint_mass():
    sim = Simulation(Config(n_agents=3), "mica_ptr", 2)
    sim.phase_decide(0)
    model = TaskRelevanceModel(sim, sim.agents[0])
    delta = np.zeros_like(sim.Lc)
    delta[sim.cfg.grid // 2, sim.cfg.grid // 2] = 4.0
    assert model.evidence_voi([delta], [sim.agents[0].pos])[0] > 0

