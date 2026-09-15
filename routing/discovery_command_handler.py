import json
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import uuid4

import paho.mqtt.client as mqtt

from core import DeviceDiscovery
from .command_handler import CommandHandler
from .topology_provider import TopologyProvider

logger = logging.getLogger(__name__)


class DiscoveryCommandHandler(CommandHandler, TopologyProvider):
    """Orchestrates Device Discovery over MQTT Pub/Sub:
    1. Retained Topology: Publishes devices inventory to 'state/system/topology' on connect.
    2. State Snapshot: Responds to 'cmd/system/state/request' with current SSOT state store values.
    3. Legacy Interface Preservation: Maintains handle() and sync_topology() contracts.
    """

    def __init__(self, device_discovery: DeviceDiscovery, state_store: Optional[Dict[str, Any]] = None) -> None:
        self.device_discovery = device_discovery
        self.state_store = state_store if state_store is not None else {}

    def set_state_store(self, state_store: Dict[str, Any]) -> None:
        """Dynamically binds or updates the SSOT state store reference."""
        self.state_store = state_store

    def can_handle(self, payload: Dict[str, Any]) -> bool:
        """Legacy frame/payload command matching."""
        action = payload.get("action", "") or payload.get("command", "")
        return str(action).upper() == "DISCOVER"

    def _serialize_device(self, dev: Any) -> Any:
        """Safely convert a device object to a JSON-serializable format."""
        to_dict_fn = getattr(dev, "to_dict", None)
        if callable(to_dict_fn):
            return to_dict_fn()
        if isinstance(dev, (dict, list, str, int, float, bool, type(None))):
            return dev
        return str(dev)

    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Legacy local handling returning structured dictionary payload."""
        devices = self.device_discovery.get_all_devices()

        return {
            "status": "SUCCESS",
            "message": f"Discovered {len(devices)} device(s) locally.",
            "topology": [self._serialize_device(dev) for dev in devices],
        }

    def sync_topology(self) -> List[Any]:
        """Implementation of TopologyProvider interface contract."""
        return self.device_discovery.get_all_devices()

    # =====================================================================
    # MQTT PUB/SUB DISCOVERY METHODS
    # =====================================================================

    def get_topology_payload(self) -> Dict[str, Any]:
        """Serializes current registry inventory for MQTT topology broadcast."""
        devices = self.device_discovery.get_all_devices()
        topology_list = [self._serialize_device(dev) for dev in devices]

        return {
            "timestamp": int(time.time()),
            "total_devices": len(topology_list),
            "devices": topology_list,
        }

    def publish_retained_topology(self, client: mqtt.Client) -> None:
        """Publishes initial device inventory as a Retained MQTT message.
        Newly connected clients receive this automatically upon subscribing to 'state/system/topology'.
        """
        payload = self.get_topology_payload()
        client.publish("state/system/topology", json.dumps(payload), qos=1, retain=True)
        logger.info("[DISCOVERY] Published retained device topology to 'state/system/topology'")

    def handle_state_request(self, client: mqtt.Client, message_payload: bytes) -> None:
        """Handles explicit on-demand full state snapshot requests published to 'cmd/system/state/request'."""
        try:
            req = json.loads(message_payload.decode("utf-8"))
            reply_to = str(req.get("reply_to", "response/system/state"))

            # Basic guard against topic injection/wildcard abuse
            if "#" in reply_to or "+" in reply_to:
                logger.warning(f"[DISCOVERY] Rejected invalid reply_to topic with wildcards: '{reply_to}'")
                return

            snapshot = {
                "request_id": req.get("request_id", f"req-{uuid4().hex[:8]}"),
                "timestamp": int(time.time()),
                "states": self.state_store,
            }
            client.publish(reply_to, json.dumps(snapshot), qos=1)
            logger.info(f"[DISCOVERY] Dispatched full state snapshot to '{reply_to}'")
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(f"[DISCOVERY] Failed to decode state request payload: {exc}")
        except Exception:
            logger.exception("[DISCOVERY] Unexpected failure processing state request")