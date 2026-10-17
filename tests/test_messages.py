import json
import uuid
import pytest
from engine.messages import parse_command, BadMessage

def cmd(**changes):
    msg = {"schema_version": 1, "correlation_id": str(uuid.uuid4()),
    "payload": {"control": "throttle", "value": 0.65}}
    msg.update(changes)
    return json.dumps(msg).encode()

def test_valid_command():
    c = parse_command("android-controller-01", cmd())
    assert c.client_id == "android-controller-01"

def test_missing_correlation_id():
    raw = json.dumps({"schema_version": 1, "payload": {}}).encode()
    with pytest.raises(BadMessage):
        parse_command("c", raw)

def test_unknown_version():
    with pytest.raises(BadMessage):
        parse_command("c", cmd(schema_version=2))

def test_not_json_and_too_large():
    with pytest.raises(BadMessage):
        parse_command("c", b"nope")
    with pytest.raises(BadMessage):
        parse_command("c", b"x" * (128 * 1024 + 1))