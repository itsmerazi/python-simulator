import json
import uuid

import engine.protocol
from engine.protocol import Protocol
from engine.simulation_core import SimulationCore

def cmd(cid=None, value=0.65, control="throttle"):
    msg = {"schema_version": 1, "correlation_id": cid or str(uuid.uuid4()),
           "payload": {"control": control, "value": value}}
    return json.dumps(msg).encode()

def test_accepted():
    record, change = Protocol(SimulationCore()).handle("c1", cmd())
    assert record["status"] == "accepted" and change == {"throttle": 0.65}

def test_rejected_without_correlation_id():
    raw = b'{"schema_version": 1, "payload": {}}'
    record, change = Protocol(SimulationCore()).handle("c1", raw)
    assert record["status"] == "rejected" and change is None

def test_rejected_out_of_range():
    record, change = Protocol(SimulationCore()).handle("c1", cmd(value=5))
    assert record["reason"] == "out_of_range" and change is None

def test_duplicate_is_applied_once():
    p = Protocol(SimulationCore())
    cid = str(uuid.uuid4())
    p.handle("c1", cmd(cid, 0.1))
    record, change = p.handle("c1", cmd(cid, 0.9))
    assert record["status"] == "duplicate" and change is None
    assert p.core.state["throttle"] == 0.1

def test_same_id_from_another_client_is_independent():
    p = Protocol(SimulationCore())
    cid = str(uuid.uuid4())
    p.handle("c1", cmd(cid, 0.1))
    record, change = p.handle("c2", cmd(cid, 0.9))  # c2 reuses c1's ID
    assert record["status"] == "accepted" and record["client_id"] == "c2"
    assert change == {"throttle": 0.9}

def test_registry_is_bounded(monkeypatch):
    monkeypatch.setattr(engine.protocol, "REGISTRY_MAX", 3)
    p = Protocol(SimulationCore())
    for _ in range(10):
        p.handle("c1", cmd())
    assert len(p.seen) == 3