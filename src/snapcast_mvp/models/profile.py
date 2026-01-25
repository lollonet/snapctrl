"""Server profile data model for connection configuration."""

from dataclasses import dataclass, replace
from typing import Self


@dataclass(frozen=True)
class ServerProfile:
    """Connection profile for a Snapcast server.

    Attributes:
        id: Unique identifier for the profile.
        name: Human-readable name (e.g., "Living Room", "Basement").
        host: Server hostname or IP address.
        port: TCP port (default 1705).
        auto_connect: Whether to auto-connect on startup.
    """

    id: str
    name: str
    host: str
    port: int = 1705
    auto_connect: bool = False

    def with_auto_connect(self, auto_connect: bool) -> Self:
        """Return a copy with auto_connect changed.

        Args:
            auto_connect: New auto_connect value.

        Returns:
            New ServerProfile with updated auto_connect.
        """
        return replace(self, auto_connect=auto_connect)


def create_profile(
    name: str,
    host: str,
    port: int = 1705,
    auto_connect: bool = False,
) -> ServerProfile:
    """Create a new ServerProfile with a generated ID.

    Args:
        name: Human-readable name.
        host: Server hostname or IP.
        port: TCP port.
        auto_connect: Whether to auto-connect on startup.

    Returns:
        New ServerProfile with unique ID based on host:port.
    """
    import hashlib

    profile_id = hashlib.md5(f"{host}:{port}".encode()).hexdigest()[:8]
    return ServerProfile(
        id=profile_id,
        name=name,
        host=host,
        port=port,
        auto_connect=auto_connect,
    )
