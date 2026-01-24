"""Server connection model."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Server:
    """Snapcast server connection info.

    Attributes:
        name: Human-readable name for this server profile.
        host: Server hostname or IP address.
        port: WebSocket port (default 1704).
        auto_connect: Whether to auto-connect on startup.
    """

    name: str
    host: str
    port: int = 1704
    auto_connect: bool = False

    @property
    def url(self) -> str:
        """Return the WebSocket URL for this server."""
        return f"ws://{self.host}:{self.port}/jsonrpc"

    @property
    def websocket_url(self) -> str:
        """Return the WebSocket URL for this server."""
        return self.url
