import logging
import os
import signal
import sys
from pathlib import Path
from typing import Any, Dict

import paho.mqtt.client as mqtt

from core import DeviceDiscovery, DeviceFactory
from routing import DiscoveryCommandHandler

# Paths & Environment Configurations
DEVICES_CONFIG_PATH = Path(os.getenv("DEVICES_CONFIG_PATH", "config/devices.json"))

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
USE_TLS = os.getenv("USE_TLS", "true").lower() == "true"
MQTT_PORT = int(os.getenv("MQTT_PORT", "8883" if USE_TLS else "1883"))
MQTT_CLIENT_ID = os.getenv("MQTT_CLIENT_ID", "python-sim-engine-ssot")

# TLS Certificate Configurations
CA_CERT_PATH = os.getenv("CA_CERT_PATH", "certs/ca_cert.pem")
CLIENT_CERT_PATH = os.getenv("CLIENT_CERT_PATH", "certs/simulator_client_cert.pem")
PRIVATE_KEY_PATH = os.getenv("PRIVATE_KEY_PATH", "certs/simulator_client_key.pem")
TLS_INSECURE = os.getenv("TLS_INSECURE", "false").lower() == "true"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def validate_paths() -> None:
    if not DEVICES_CONFIG_PATH.exists():
        logging.error("Configuration file not found at %s", DEVICES_CONFIG_PATH)
        sys.exit(1)

    if USE_TLS:
        for path_name, path_str in [
            ("CA_CERT_PATH", CA_CERT_PATH),
            ("CLIENT_CERT_PATH", CLIENT_CERT_PATH),
            ("PRIVATE_KEY_PATH", PRIVATE_KEY_PATH),
        ]:
            if not Path(path_str).exists():
                logging.error("TLS Certificate missing [%s]: %s", path_name, path_str)
                sys.exit(1)


def main() -> None:
    validate_paths()

    # 1. Initialize Registry and Populate locally from devices.json
    device_discovery = DeviceDiscovery()
    parsed_objects = DeviceFactory.from_file(DEVICES_CONFIG_PATH)
    device_discovery.replace_all(parsed_objects)

    # Populate SSOT state store for Discovery state requests
    state_store: Dict[str, Dict[str, Any]] = {
        getattr(dev, "id", str(dev)): {"state": getattr(dev, "state", "OFF")}
        for dev in parsed_objects
    }

    # 2. Instantiate Discovery Command Handler
    discovery_handler = DiscoveryCommandHandler(
        device_discovery=device_discovery,
        state_store=state_store,
    )

    # 3. Configure MQTT Client
    mqtt_client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=MQTT_CLIENT_ID,
    )

    if USE_TLS:
        logging.info("[TLS] Configuring secure MQTT connection using CA: %s", CA_CERT_PATH)
        mqtt_client.tls_set(
            ca_certs=CA_CERT_PATH,
            certfile=CLIENT_CERT_PATH,
            keyfile=PRIVATE_KEY_PATH,
        )
        if TLS_INSECURE:
            logging.warning("[TLS] Insecure verification explicitly enabled via TLS_INSECURE flag.")
            mqtt_client.tls_insecure_set(True)

    def on_connect(client: mqtt.Client, userdata: Any, flags: Any, reason_code: Any, properties: Any) -> None:
        if reason_code.is_failure:
            logging.error("Failed to connect to MQTT broker. Code: %s", reason_code)
            return

        logging.info("Connected to MQTT broker (%s:%s)", MQTT_HOST, MQTT_PORT)
        discovery_handler.publish_retained_topology(client)
        client.subscribe("cmd/system/state/request", qos=1)

    def on_state_request_msg(client: mqtt.Client, userdata: Any, msg: mqtt.MQTTMessage) -> None:
        discovery_handler.handle_state_request(client, msg.payload)

    mqtt_client.on_connect = on_connect
    mqtt_client.message_callback_add("cmd/system/state/request", on_state_request_msg)

    # Setup Graceful Shutdown Strategy
    def handle_shutdown(signum: int, frame: Any) -> None:
        logging.info("Signal received, shutting down MQTT engine gracefully...")
        mqtt_client.disconnect()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    # 4. Connect to Broker and Start Loop
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
    except OSError as exc:
        logging.error("Failed to connect to MQTT broker at %s:%s - %s", MQTT_HOST, MQTT_PORT, exc)
        sys.exit(1)

    logging.info("Python Digital Twin Engine Running (Discovery Module Active)...")
    mqtt_client.loop_forever()


if __name__ == "__main__":
    main()