import os
from dataclasses import dataclass

Q1_SIZE = 256  # inbound commands waiting for the engine loop
Q2_SIZE = 256  # outbound audit records and telemetry waiting to be sent
TICK_HZ = 60  # physics steps per second (fixed time step)
MAX_TELEMETRY_HZ = 30  # hard ceiling on telemetry (Section 3, point 3)


@dataclass(frozen=True)
class Settings:
    iot_endpoint: str
    client_id: str
    cert_path: str
    key_path: str
    ca_path: str
    telemetry_hz: float  # optional: default 30, never above 30


def _need(name):
    value = os.environ.get(name)
    if not value:
        raise SystemExit("missing environment variable " + name)
    return value


def _telemetry_hz():
    text = os.environ.get("TELEMETRY_HZ", str(MAX_TELEMETRY_HZ))
    try:
        hz = float(text)
    except ValueError:
        hz = 0.0
        if not 0 < hz <= MAX_TELEMETRY_HZ:
            raise SystemExit("TELEMETRY_HZ must be above 0 and at most %d" % MAX_TELEMETRY_HZ)
    return hz

def load_settings():
    return Settings(
        iot_endpoint=_need("IOT_ENDPOINT"),
        client_id=_need("CLIENT_ID"),
        cert_path=_need("CERT_PATH"),
        key_path=_need("KEY_PATH"),
        ca_path=_need("CA_PATH"),
        telemetry_hz=_telemetry_hz(),
    )

if __name__ == "__main__":
    print(load_settings())