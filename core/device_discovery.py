import threading
from typing import Any, Dict, List, Optional


class DeviceDiscovery:
    """Thread-safe dynamic device registry."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: Dict[str, Any] = {}

    def register_device(self, device: Any) -> None:
        with self._lock:
            self._devices[device.device_id] = device

    def replace_all(self, devices: List[Any]) -> None:
        """Atomically replaces all registered devices to prevent read-during-sync race conditions."""
        with self._lock:
            self._devices = {dev.device_id: dev for dev in devices}

    def get_device(self, device_id: str) -> Optional[Any]:
        with self._lock:
            return self._devices.get(device_id)

    def get_all_devices(self) -> List[Any]:
        with self._lock:
            return list(self._devices.values())

    def clear(self) -> None:
        with self._lock:
            self._devices.clear()