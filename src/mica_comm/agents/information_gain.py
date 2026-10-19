"""Task-weighted Bayesian surprise without a model of receiver decisions.

Evidence is valued as sum_c w(c) KL(Bern(q_c) || Bern(p_c)), in nats,
where p is the publicly known belief and q is its update by the actual payload.
This is realized information gain (Bayesian surprise), not expected entropy
reduction: a surprising positive detection must retain value even if entropy rises.
Weights describe geometric accessibility from publicly reported receiver positions.
No receiver policy, private belief, private target, or world truth is inspected.
"""

import numpy as np

from mica_comm.world.belief import box_sum, sigmoid


def bernoulli_kl_from_logits(p_logits, q_logits):
    """Stable elementwise KL(q || p), including effectively certain beliefs."""
    q = sigmoid(q_logits)
    log_p = -np.logaddexp(0.0, -p_logits)
    log_not_p = -np.logaddexp(0.0, p_logits)
    log_q = -np.logaddexp(0.0, -q_logits)
    log_not_q = -np.logaddexp(0.0, q_logits)
    return np.maximum(q * (log_q - log_p) + (1.0 - q) * (log_not_q - log_not_p), 0.0)


class InformationGainModel:
    """A drop-in evidence/intent valuation interface for MICA's scheduler.

    ``weighted=False`` removes only the evidence accessibility weights, providing
    an information-gain ablation with the same intent and confirmation rules.
    """

    def __init__(self, sim, sender, weighted=True):
        self.cfg, self.sim, self.sender = sim.cfg, sim, sender
        self.X, self.Y = sender._X, sender._Y
        self.live = ~sim.declared.reshape(sim.Lc.shape)
        self.receivers = [j for j in sim.team_pos if j != sender.idx]
        self.weights = self._accessibility(self.receivers)
        if not weighted:
            self.weights = np.ones_like(sim.Lc) if self.receivers else np.zeros_like(sim.Lc)

    def _accessibility(self, receivers):
        """Best receiver discount for reaching a cell's sensing footprint.

        A max avoids counting the same cell repeatedly when the team grows.
        Public positions may be stale; no extrapolated receiver actions are used.
        """
        weight = np.zeros_like(self.sim.Lc)
        for j in receivers:
            x, y = self.sim.team_pos[j]
            distance = np.maximum(np.abs(self.X - x) - self.cfg.sense_radius, 0)
            distance = distance + np.maximum(np.abs(self.Y - y) - self.cfg.sense_radius, 0)
            weight = np.maximum(weight, 1.0 / (1.0 + self.cfg.distance_discount * distance))
        return weight

    def evidence_voi(self, delta_llrs, new_positions):
        """Score each payload against the same public prior; position is metadata."""
        return [
            float(
                (
                    self.weights
                    * self.live
                    * bernoulli_kl_from_logits(self.sim.Lc, self.sim.Lc + d)
                ).sum()
            )
            for d in delta_llrs
        ]

    def intent_voi(self, target):
        """Value the changed public spatial reservation, without action prediction.

        Only lower-priority receivers use this sender's intent for deconfliction.
        Releasing an old reservation and establishing a new one both carry value.
        """
        receivers = [j for j in self.receivers if j > self.sender.idx]
        if not receivers:
            return 0.0
        previous = self.sim.team_intent.get(self.sender.idx)
        if previous == target:
            return 0.0
        old = (
            divmod(previous, self.cfg.grid)
            if previous is not None
            else self.sim.team_pos.get(self.sender.idx, self.sender.pos)
        )
        new = divmod(target, self.cfg.grid)

        def reservation(point):
            x, y = point
            return np.exp(
                -((self.X - x) ** 2 + (self.Y - y) ** 2) / (2.0 * self.cfg.repulsion_sigma**2)
            )

        mass = sigmoid(self.sim.Lc + self.sender.pending_llr) * self.live
        if self.sender.confirmed_pending:
            mass.reshape(-1)[list(self.sender.confirmed_pending)] = 0.0
        change = np.abs(reservation(new) - reservation(old))
        return float(self.cfg.intent_value * (mass * change * self._accessibility(receivers)).sum())


class TaskRelevanceModel(InformationGainModel):
    """Public task-relevance value based on counterfactual search coverage.

    This follows the paper's conclusion that value need only rank messages by
    coarse task relevance.  It measures the change in survivor mass inside a
    planner's sensing footprint, then weights target cells by public receiver
    accessibility.  It does not simulate receiver choices or inspect private
    evidence, so it is cheaper and less brittle than ToM.
    """

    def evidence_voi(self, delta_llrs, new_positions):
        p = sigmoid(self.sim.Lc) * self.live
        base = box_sum(p, self.cfg.sense_radius)
        return [
            float(
                np.partition(
                    (
                        self.weights
                        * np.abs(
                            box_sum(
                                sigmoid(self.sim.Lc + d) * self.live,
                                self.cfg.sense_radius,
                            )
                            - base
                        )
                    ).reshape(-1),
                    -max(len(self.receivers), 1),
                )[-max(len(self.receivers), 1) :].sum()
            )
            for d in delta_llrs
        ]

