import json
import uuid
from dataclasses import dataclass

SCHEMA_VERSION = 1
MAX_BYTES = 128 * 1024  # AWS IoT Core message limit

class BadMessage(Exception):
    # The command is rejected; the text becomes the reason in the audit record.
    pass

@dataclass(frozen=True)
class Command:
    client_id: str  # taken from the topic, never from the payload
    correlation_id: str
    payload: dict

def _is_uuid4(text):
    try:
        return uuid.UUID(text).version == 4
    except ValueError:
        return False

def parse_command(client_id, raw):
    if len(raw) > MAX_BYTES:
        raise BadMessage("too_large")
    try:
        msg = json.loads(raw)
    except ValueError:
        raise BadMessage("not_json")

    if not isinstance(msg, dict):
        raise BadMessage("not_an_object")
    if msg.get("schema_version") != SCHEMA_VERSION:
        raise BadMessage("unknown_schema_version")

    cid = msg.get("correlation_id")
    if not isinstance(cid, str) or not _is_uuid4(cid):
        raise BadMessage("bad_correlation_id")

    payload = msg.get("payload")
    if not isinstance(payload, dict):
        raise BadMessage("bad_payload")

    return Command(client_id, cid, payload)

def audit(client_id, correlation_id, status, reason=None):
    return {"schema_version": SCHEMA_VERSION, "correlation_id": correlation_id,
            "status": status, "reason": reason, "client_id": client_id}

def telemetry(state, correlation_id=None, seq=0):
    # seq counts snapshots, so a viewer can spot a gap or drop an older one.
    return {"schema_version": SCHEMA_VERSION, "seq": seq,
            "correlation_id": correlation_id, "state": state}

def encode(message):
    data = json.dumps(message, separators=(",", ":")).encode()

    if len(data) > MAX_BYTES:
        raise ValueError("message too large")
    return data