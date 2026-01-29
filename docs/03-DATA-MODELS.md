# SnapCTRL - Data Models

## Overview

All models are implemented as **frozen dataclasses** for immutability and thread safety.

## Core Models

### Server

```python
@dataclass(frozen=True)
class Server:
    """Snapcast server connection info.

    Snapcast uses raw TCP sockets with JSON-RPC, NOT WebSocket.
    Default port is 1705.
    """
    name: str
    host: str
    port: int = 1705
    auto_connect: bool = False

    @property
    def address(self) -> str:
        """Return the server address (host:port)."""
        return f"{self.host}:{self.port}"
```

### ServerProfile

```python
@dataclass(frozen=True)
class ServerProfile:
    """Saved server profile for connection configuration."""
    id: str
    name: str
    host: str
    port: int = 1705
    auto_connect: bool = False
```

### Client

```python
@dataclass(frozen=True)
class Client:
    """A Snapcast client (audio endpoint/speaker)."""
    id: str
    host: str
    name: str = ""
    mac: str = ""
    volume: int = 50           # 0-100
    muted: bool = False
    connected: bool = True
    latency: int = 0           # milliseconds offset
    snapclient_version: str = ""
    last_seen_sec: int = 0     # Unix timestamp (seconds)
    last_seen_usec: int = 0    # Microseconds part
    host_os: str = ""          # e.g., "Linux"
    host_arch: str = ""        # e.g., "aarch64"
    host_name: str = ""        # Device hostname

    @property
    def display_name(self) -> str:
        """Return name or host as fallback for display."""
        return self.name or self.host

    @property
    def last_seen_ago(self) -> str:
        """Return human-readable time since last seen."""

    @property
    def display_system(self) -> str:
        """Return 'OS (arch)' string, e.g., 'Linux (aarch64)'."""

    @property
    def display_latency(self) -> str:
        """Return latency as string with ms suffix, e.g., '+30 ms'."""
```

### Group

```python
@dataclass(frozen=True)
class Group:
    """A group of clients sharing an audio source."""
    id: str
    name: str = ""
    stream_id: str = ""        # Current source ID
    muted: bool = False
    client_ids: list[str] = field(default_factory=list)

    @property
    def client_count(self) -> int:
        """Return number of clients in group."""
        return len(self.client_ids)
```

### Source

```python
@dataclass(frozen=True)
class Source:
    """An audio source/stream in the Snapcast server."""
    id: str
    name: str = ""
    status: str = "idle"       # idle, playing
    stream_type: str = ""      # pipe, librespot, airplay, meta, etc.
    codec: str = ""            # flac, pcm, opus, ogg, etc.
    sample_format: str = ""    # e.g., "48000:16:2"
    uri_scheme: str = ""       # pipe, librespot, airplay, meta, etc.
    uri_raw: str = ""          # Raw URI string for debugging

    # Track metadata (from Snapcast or MPD)
    meta_title: str = ""
    meta_artist: str = ""
    meta_album: str = ""
    meta_art_url: str = ""

    @property
    def is_playing(self) -> bool:
        """Return True if stream is currently playing."""
        return self.status == "playing"

    @property
    def is_idle(self) -> bool:
        """Return True if stream is idle."""
        return self.status == "idle"

    @property
    def display_codec(self) -> str:
        """Return codec for display, with fallback."""
        return self.codec or self.stream_type or "unknown"

    @property
    def display_format(self) -> str:
        """Return sample format in human-readable form (e.g., '48kHz/16bit/stereo').

        Parses sample_format string like '48000:16:2' into readable components.
        """

    @property
    def has_metadata(self) -> bool:
        """Return True if source has track metadata."""
        return bool(self.meta_title or self.meta_artist)

    @property
    def display_now_playing(self) -> str:
        """Return formatted 'Now Playing' string."""
        # Returns "Title — Artist" if metadata available
```

### ServerState

```python
@dataclass(frozen=True)
class ServerState:
    """Complete snapshot of server state at a point in time."""
    server: Server
    groups: tuple[Group, ...] = ()
    clients: tuple[Client, ...] = ()
    sources: tuple[Source, ...] = ()
    connected: bool = False
    version: str = ""          # Snapserver version
    host: str = ""             # Server's hostname
    mac: str = ""              # Server's MAC address

    @property
    def group_count(self) -> int:
        return len(self.groups)

    @property
    def client_count(self) -> int:
        return len(self.clients)

    @property
    def source_count(self) -> int:
        return len(self.sources)

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
```

---

### SourceStatus (Enum)

```python
class SourceStatus(str, Enum):
    """Status of an audio source/stream."""
    IDLE = "idle"
    PLAYING = "playing"
    UNKNOWN = "unknown"
```

### MPD Models

See `src/snapctrl/api/mpd/types.py` for the full definitions.

```python
@dataclass(frozen=True)
class MpdTrack:
    """Track metadata from MPD."""
    title: str = ""
    artist: str = ""
    album: str = ""
    file: str = ""

@dataclass(frozen=True)
class MpdAlbumArt:
    """Album art data from MPD or external providers."""
    data: bytes = b""
    mime_type: str = ""
```

---

## JSON-RPC Mapping

| Snapcast Response | Model | Notes |
|-------------------|-------|-------|
| `server` | `Server` | Host, port from connection info |
| `clients[]` | `Client[]` | Individual client endpoints |
| `groups[]` | `Group[]` | Groups of clients |
| `streams[]` | `Source[]` | Audio sources (called "streams" in API) |

---

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Frozen dataclasses** | Immutable state, thread-safe for QThread |
| **Tuples instead of lists** | Hashable, prevents accidental mutation |
| **@property for computed** | Clean API, no stored redundancy |
| **Optional fields with defaults** | Graceful handling of missing data |

---

*Next: [UI/UX Design](04-UI-UX.md) →*

*Last updated: 2026-01-29*
