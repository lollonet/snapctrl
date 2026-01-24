"""Client model representing a Snapcast audio endpoint."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Client:
    """A Snapcast client (audio endpoint/speaker).

    Attributes:
        id: Unique client identifier from server.
        host: Client's IP address or hostname.
        name: Human-readable name (empty string if unset).
        mac: MAC address (empty string if unavailable).
        volume: Volume level 0-100.
        muted: Whether audio is muted.
        connected: Whether client is connected to server.
        latency: Audio latency in milliseconds.
        snapclient_version: Version of snapclient running on client.
    """

    id: str
    host: str
    name: str = ""
    mac: str = ""
    volume: int = 50
    muted: bool = False
    connected: bool = True
    latency: int = 0
    snapclient_version: str = ""

    @property
    def display_name(self) -> str:
        """Return name or host as fallback for display."""
        return self.name or self.host

    @property
    def is_muted(self) -> bool:
        """Alias for muted property."""
        return self.muted

    @property
    def is_connected(self) -> bool:
        """Alias for connected property."""
        return self.connected
