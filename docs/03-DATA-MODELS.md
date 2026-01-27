# Snapcast MVP - Data Models

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
    latency: int = 0           # milliseconds
    snapclient_version: str = ""

    @property
    def display_name(self) -> str:
        """Return name or host as fallback for display."""
        return self.name or self.host
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
    client_ids: tuple[str, ...] = ()

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
    stream_type: str = ""      # flac, spotify, airplay, etc.

    @property
    def is_playing(self) -> bool:
        """Return True if stream is currently playing."""
        return self.status == "playing"

    @property
    def is_idle(self) -> bool:
        """Return True if stream is idle."""
        return self.status == "idle"
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

*Last updated: 2025-01-26*
