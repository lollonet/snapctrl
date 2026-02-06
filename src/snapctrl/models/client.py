"""Client model representing a Snapcast audio endpoint."""

import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Time thresholds for last_seen display (in seconds)
_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR = 3600
_SECONDS_PER_DAY = 86400


def _format_time_ago(seconds: int) -> str:
    """Format seconds as human-readable time ago string."""
    if seconds < 2:  # noqa: PLR2004
        return "just now"
    if seconds < _SECONDS_PER_MINUTE:
        return f"{seconds}s ago"
    if seconds < _SECONDS_PER_HOUR:
        return f"{seconds // _SECONDS_PER_MINUTE}m ago"
    if seconds < _SECONDS_PER_DAY:
        return f"{seconds // _SECONDS_PER_HOUR}h ago"
    return f"{seconds // _SECONDS_PER_DAY}d ago"


@dataclass(frozen=True, slots=True)
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
        latency: Configured latency offset in milliseconds.
        snapclient_version: Version of snapclient running on client.
        last_seen_sec: Unix timestamp (seconds) when client was last seen.
        last_seen_usec: Microseconds part of last seen timestamp.
        host_os: Operating system of the client device.
        host_arch: CPU architecture of the client device.
        host_name: Hostname of the client device.
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
    last_seen_sec: int = 0
    last_seen_usec: int = 0
    host_os: str = ""
    host_arch: str = ""
    host_name: str = ""

    def __post_init__(self) -> None:
        """Validate and clamp volume to 0-100 range."""
        if self.volume < 0 or self.volume > 100:  # noqa: PLR2004
            clamped = max(0, min(100, self.volume))
            logger.warning(
                "Client %s volume %d out of range, clamped to %d",
                self.id,
                self.volume,
                clamped,
            )
            object.__setattr__(self, "volume", clamped)

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

    @property
    def last_seen_ago(self) -> str:
        """Return human-readable time since last seen."""
        if self.last_seen_sec == 0:
            return "unknown"
        delta = int(time.time()) - self.last_seen_sec
        return _format_time_ago(delta)

    @property
    def display_system(self) -> str:
        """Return OS and architecture for display."""
        parts: list[str] = []
        if self.host_os:
            parts.append(self.host_os)
        if self.host_arch:
            parts.append(self.host_arch)
        return " / ".join(parts) if parts else ""

    @property
    def display_latency(self) -> str:
        """Return latency offset for display."""
        if self.latency == 0:
            return "0ms (no offset)"
        return f"{self.latency}ms"
