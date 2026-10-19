"""Request-driven protocol primitives, independent of the legacy scheduler."""

import math
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np

from mica_comm.world.belief import Obs, SensorModel

from .protocol import EvidenceReply, EvidenceRequest, TargetLease, UniqueLedger


@dataclass(frozen=True)
class ProtocolCost:
    """Fixed control costs plus a per-observation evidence encoding."""

    request_bits: int = 48
    reply_header_bits: int = 32
    record_bits: int = 64

    def __post_init__(self):
        if min(self.request_bits, self.reply_header_bits, self.record_bits) <= 0:
            raise ValueError("protocol bit costs must be positive")

    def reply_bits(self, n_records: int) -> int:
        if n_records < 0:
            raise ValueError("record count cannot be negative")
        return self.reply_header_bits + self.record_bits * n_records


class EvidenceResponder:
    """Answer only with the responder's own observations relevant to a query."""

    def __init__(self, agent_id: int, sensor: SensorModel, cost: ProtocolCost = ProtocolCost()):
        self.agent_id = agent_id
        self.sensor = sensor
        self.cost = cost

    def respond(self, request: EvidenceRequest, own_records: Iterable[Obs]) -> EvidenceReply:
        n = self.sensor.grid
        x, y = divmod(request.cell, n)
        relevant = []
        for record in own_records:
            if record.agent != self.agent_id:
                continue
            sx, sy = self.sensor.window(record.pos)
            if sx.start <= x < sx.stop and sy.start <= y < sy.stop:
                relevant.append(record)
        records = tuple(sorted(relevant, key=lambda item: (item.t, item.agent)))
        return EvidenceReply(
            request_id=request.request_id,
            responder=self.agent_id,
            records=records,
            bits=self.cost.reply_bits(len(records)),
        )


class RequestCoordinator:
    """Resolve requests, deduplicate delivered evidence, and account all bits."""

    def __init__(self, budget_bits: int, cost: ProtocolCost = ProtocolCost()):
        if budget_bits < 0:
            raise ValueError("budget_bits cannot be negative")
        self.budget_bits = budget_bits
        self.cost = cost
        self.spent_bits = 0
        self.ledger = UniqueLedger()

    def exchange(self, request, responder, peer_records, now):
        if not request.issued_at <= now <= request.expires_at:
            raise ValueError("request is not active")
        reply = responder.respond(request, peer_records)
        cost = self.cost.request_bits + reply.bits
        if self.spent_bits + cost > self.budget_bits:
            return EvidenceReply(request.request_id, reply.responder, (), 0), ()
        self.spent_bits += cost
        return reply, self.ledger.accept(reply.records)


def active_lease_conflicts(leases: Sequence[TargetLease], cell: int, t: int, owner: int) -> bool:
    """Whether another agent has an unexpired commitment to the same cell."""
    return any(lease.agent != owner and lease.cell == cell and lease.active(t) for lease in leases)


def select_query_cell(
    belief: np.ndarray,
    candidates: Iterable[int],
    grid: int,
    leases: Sequence[TargetLease],
    owner: int,
    t: int,
    min_entropy: float = 0.0,
):
    """Choose the most uncertain unleased candidate, breaking ties by cell ID."""
    values = np.asarray(belief, dtype=float).reshape(-1)
    if values.size != grid * grid or np.any(~np.isfinite(values)):
        raise ValueError("belief must contain one finite probability per grid cell")
    if np.any((values < 0.0) | (values > 1.0)):
        raise ValueError("belief probabilities must lie in [0, 1]")
    options = sorted({int(cell) for cell in candidates})
    if any(cell < 0 or cell >= grid * grid for cell in options):
        raise ValueError("candidate cell is outside the grid")
    options = [cell for cell in options if not active_lease_conflicts(leases, cell, t, owner)]
    if not options:
        return None

    def entropy(cell):
        p = float(values[cell])
        return -sum(q * math.log2(q) for q in (p, 1.0 - p) if q > 0.0)

    selected = max(options, key=lambda cell: (entropy(cell), -cell))
    return selected if entropy(selected) >= min_entropy else None


def fuse_unique_records(shared_llr: np.ndarray, records: Iterable[Obs], sensor: SensorModel):
    """Add already-deduplicated observations to the common log-odds map."""
    for record in records:
        sensor.apply(shared_llr, record)
    return shared_llr
