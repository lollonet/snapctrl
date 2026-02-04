"""ServerState model representing complete server snapshot."""

from dataclasses import dataclass, field

from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.server import Server
from snapctrl.models.source import Source


@dataclass(frozen=True, slots=True)
class ServerState:
    """Complete snapshot of server state at a point in time.

    Attributes:
        server: The server connection info.
        groups: List of groups on the server.
        clients: List of all clients.
        sources: List of available audio sources/streams.
        connected: Whether currently connected to server.
        version: Snapserver version string.
        host: Server's hostname (as reported by server).
        mac: Server's MAC address (as reported by server).
    """

    server: Server
    groups: list[Group] = field(default_factory=list)
    clients: list[Client] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    connected: bool = False
    version: str = ""
    host: str = ""
    mac: str = ""

    @property
    def group_count(self) -> int:
        """Return number of groups."""
        return len(self.groups)

    @property
    def client_count(self) -> int:
        """Return number of clients."""
        return len(self.clients)

    @property
    def source_count(self) -> int:
        """Return number of sources."""
        return len(self.sources)

    @property
    def is_connected(self) -> bool:
        """Alias for connected property."""
        return self.connected

    def get_client(self, client_id: str) -> Client | None:
        """Return client by ID or None if not found."""
        for client in self.clients:
            if client.id == client_id:
                return client
        return None

    def get_group(self, group_id: str) -> Group | None:
        """Return group by ID or None if not found."""
        for group in self.groups:
            if group.id == group_id:
                return group
        return None

    def get_source(self, source_id: str) -> Source | None:
        """Return source by ID or None if not found."""
        for source in self.sources:
            if source.id == source_id:
                return source
        return None
