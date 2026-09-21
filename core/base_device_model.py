from typing import Any, Dict


class BaseDeviceModel:
    """Encapsulates device runtime state and behavior contract for discovery and execution."""

    def __init__(self, raw_data: Dict[str, Any], id_key: str) -> None:
        self._raw_data: Dict[str, Any] = raw_data
        self.device_id: str = raw_data[id_key]

    def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executes operational commands against local state (ON, OFF, TOGGLE, SET_BRIGHTNESS, etc.)."""
        action = str(payload.get("action", "") or payload.get("command", "")).upper()

        if "state" in self._raw_data and isinstance(self._raw_data["state"], dict):
            state = self._raw_data["state"]
            state["command"] = action

            if action in ["ON", "TURN_ON_ALL"]:
                state["isOn"] = True
            elif action in ["OFF", "TURN_OFF_ALL"]:
                state["isOn"] = False
            elif action == "TOGGLE":
                state["isOn"] = not state.get("isOn", False)
            elif action == "SET_BRIGHTNESS" and "brightness" in payload:
                state["brightness"] = payload["brightness"]
            elif action == "SET_COLOR" and "color" in payload:
                state["color"] = payload["color"]

        return {
            "status": "SUCCESS",
            "deviceId": self.device_id,
            "state": self._raw_data.get("state", {}),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes internal representation for protocol framing."""
        return self._raw_data