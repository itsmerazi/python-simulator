from abc import ABC, abstractmethod
from typing import Dict, Any


class CommandHandler(ABC):
    """Abstract routing handler base class."""

    @abstractmethod
    def can_handle(self, payload: Dict[str, Any]) -> bool:
        pass

    @abstractmethod
    def handle(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        pass