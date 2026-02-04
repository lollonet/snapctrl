"""Server connection model."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Server:
    """Snapcast server connection info.

    Snapcast uses raw TCP sockets with JSON-RPC, NOT WebSocket.

    Attributes:
        name: Human-readable name for this server profile.
        host: Server hostname or IP address.
        port: TCP port (default 1705).
        auto_connect: Whether to auto-connect on startup.
    """

    name: str
    host: str
    port: int = 1705
    auto_connect: bool = False

    @property
    def address(self) -> str:
        """Return the server address (host:port)."""
        return f"{self.host}:{self.port}"
