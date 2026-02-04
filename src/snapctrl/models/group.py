"""Group model for clients sharing an audio source."""

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Group:
    """A group of clients sharing an audio source.

    Attributes:
        id: Unique group identifier from server.
        name: Human-readable group name.
        stream_id: ID of the current audio source/stream.
        muted: Whether group audio is muted.
        client_ids: List of client IDs in this group.
    """

    id: str
    name: str = ""
    stream_id: str = ""
    muted: bool = False
    client_ids: list[str] = field(default_factory=list)

    @property
    def stream(self) -> str:
        """Alias for stream_id."""
        return self.stream_id

    @property
    def client_count(self) -> int:
        """Return the number of clients in this group."""
        return len(self.client_ids)

    @property
    def is_empty(self) -> bool:
        """Return True if group has no clients."""
        return len(self.client_ids) == 0
