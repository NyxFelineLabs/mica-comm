"""Typed records for querying teammates and preventing duplicate evidence."""

from dataclasses import dataclass
from typing import Hashable, Iterable, Set, Tuple

from mica_comm.world.belief import Obs


@dataclass(frozen=True)
class EvidenceRequest:
    """A request for observations whose sensing footprint covers one cell."""

    request_id: Tuple[int, int, int]
    requester: int
    cell: int
    issued_at: int
    expires_at: int

    def __post_init__(self):
        if self.expires_at < self.issued_at:
            raise ValueError("request expiration must not precede issue time")


@dataclass(frozen=True)
class EvidenceReply:
    """A peer's evidence and the fixed protocol cost of the reply."""

    request_id: Tuple[int, int, int]
    responder: int
    records: Tuple[Obs, ...]
    bits: int


@dataclass(frozen=True)
class TargetLease:
    """Temporary public commitment that reserves a target for one agent."""

    agent: int
    cell: int
    issued_at: int
    expires_at: int

    def active(self, t: int) -> bool:
        return self.issued_at <= t <= self.expires_at


class UniqueLedger:
    """Accept each observation identity once, even across repeated replies."""

    def __init__(self):
        self._seen: Set[Hashable] = set()

    def accept(self, records: Iterable[Obs]) -> Tuple[Obs, ...]:
        accepted = []
        for record in records:
            key = (record.agent, record.t)
            if key not in self._seen:
                self._seen.add(key)
                accepted.append(record)
        return tuple(accepted)

    def __len__(self):
        return len(self._seen)
