"""Invariants of the request-driven evidence protocol."""

import numpy as np
import pytest

from mica_comm.demand.engine import (
    EvidenceResponder,
    ProtocolCost,
    RequestCoordinator,
    fuse_unique_records,
    select_query_cell,
)
from mica_comm.demand.protocol import EvidenceRequest, TargetLease, UniqueLedger
from mica_comm.world.belief import Obs, SensorModel


def test_responder_only_returns_own_records_covering_requested_cell():
    sensor = SensorModel(0.85, 0.05, 1, 12)
    records = [Obs(1, 2, (4, 4), ()), Obs(2, 2, (0, 0), ()), Obs(1, 3, (4, 4), ())]
    request = EvidenceRequest((0, 1, 4), 0, 4 * 12 + 5, 1, 3)
    reply = EvidenceResponder(2, sensor).respond(request, records)
    assert reply.records == (records[0],)


def test_coordinator_counts_control_and_payload_and_deduplicates():
    sensor = SensorModel(0.85, 0.05, 1, 12)
    cost = ProtocolCost(request_bits=10, reply_header_bits=5, record_bits=7)
    coordinator = RequestCoordinator(100, cost)
    responder = EvidenceResponder(2, sensor, cost)
    record = Obs(1, 2, (4, 4), ())
    request = EvidenceRequest((0, 1, 4), 0, 53, 1, 3)
    reply, first = coordinator.exchange(request, responder, [record], 2)
    assert first == (record,)
    assert reply.bits == 12
    assert coordinator.spent_bits == 22
    _, repeated = coordinator.exchange(request, responder, [record], 2)
    assert repeated == ()
    assert coordinator.spent_bits == 44


def test_budget_denial_does_not_partially_charge_or_deliver():
    sensor = SensorModel(0.85, 0.05, 1, 12)
    cost = ProtocolCost(request_bits=10, reply_header_bits=5, record_bits=7)
    coordinator = RequestCoordinator(21, cost)
    request = EvidenceRequest((0, 1, 4), 0, 53, 1, 3)
    reply, accepted = coordinator.exchange(
        request, EvidenceResponder(2, sensor, cost), [Obs(1, 2, (4, 4), ())], 2
    )
    assert reply.bits == 0
    assert accepted == ()
    assert coordinator.spent_bits == 0


def test_request_and_lease_boundaries_are_explicit():
    with pytest.raises(ValueError, match="expiration"):
        EvidenceRequest((0, 1, 1), 0, 1, 2, 1)
    lease = TargetLease(1, 9, 3, 5)
    assert not lease.active(2)
    assert lease.active(5)
    assert not lease.active(6)


def test_ledger_uses_agent_and_observation_slot_identity():
    record = Obs(2, 1, (0, 0), ())
    ledger = UniqueLedger()
    assert ledger.accept([record, record]) == (record,)
    assert ledger.accept([record]) == ()


def test_query_uses_maximum_entropy_and_respects_active_leases():
    belief = [0.01] * 16
    belief[3] = 0.5
    belief[7] = 0.4
    lease = TargetLease(1, 3, 1, 4)
    assert select_query_cell(belief, [3, 7], 4, [lease], owner=0, t=3) == 7
    assert select_query_cell(belief, [3], 4, [lease], owner=0, t=5) == 3


def test_fusion_applies_only_the_records_given_by_the_ledger():
    sensor = SensorModel(0.85, 0.05, 1, 8)
    record = Obs(1, 2, (3, 3), (3 * 8 + 3,))
    shared = np.zeros((8, 8))
    fused = fuse_unique_records(shared, [record], sensor)
    assert fused[3, 3] == pytest.approx(sensor.llr_pos)
