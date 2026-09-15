from typing import Any, List, Protocol, runtime_checkable


@runtime_checkable
class TopologyProvider(Protocol):
    """Abstract interface defining the contract for dynamic topology synchronization."""

    def sync_topology(self) -> List[Any]:
        """Fetches and hydrates the topology catalog, returning the updated list of devices."""
        ...