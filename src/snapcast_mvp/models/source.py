"""Source model for audio streams."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Source:
    """An audio source/stream in the Snapcast server.

    Attributes:
        id: Unique stream identifier from server.
        name: Human-readable stream name.
        status: Stream status - typically "idle" or "playing".
        stream_type: Type of stream (spotify, airplay, etc.).
    """

    id: str
    name: str = ""
    status: str = "idle"
    stream_type: str = ""

    @property
    def is_playing(self) -> bool:
        """Return True if stream is currently playing."""
        return self.status == "playing"

    @property
    def is_idle(self) -> bool:
        """Return True if stream is idle."""
        return self.status == "idle"

    @property
    def type(self) -> str:
        """Alias for stream_type."""
        return self.stream_type
