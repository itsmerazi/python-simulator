import json
from pathlib import Path
from typing import Any, Dict, List, Union

from .base_device_model import BaseDeviceModel


class DeviceFactory:
    """Factory for instantiating devices and logic gates from JSON definitions."""

    @staticmethod
    def from_file(config_path: Union[str, Path]) -> List[BaseDeviceModel]:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Config file not found: {path.resolve()}")

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return DeviceFactory.create_from_config(data)

    @staticmethod
    def create_from_config(config_data: Dict[str, Any]) -> List[BaseDeviceModel]:
        instantiated_objects: List[BaseDeviceModel] = []

        # 1. Parse bound devices (Key: deviceId)
        for dev in config_data.get("bound_devices", []):
            instantiated_objects.append(BaseDeviceModel(dev, id_key="deviceId"))

        # 2. Parse available logic gates (Key: gate_id -> mapped to device_id contract)
        for gate in config_data.get("available_gates", []):
            instantiated_objects.append(BaseDeviceModel(gate, id_key="gate_id"))

        return instantiated_objects