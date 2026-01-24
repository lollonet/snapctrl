# Snapcast MVP - Data Models

## Core Models

### Server

```python
@dataclass
class Server:
    """Snapcast server connection info."""
    name: str
    host: str
    port: int = 1704
    auto_connect: bool = False

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}/jsonrpc"
```

### Client

```python
@dataclass
class Client:
    """A Snapcast client (audio endpoint)."""
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
        return self.name or self.host
```

### Group

```python
@dataclass
class Group:
    """A group of clients sharing an audio source."""
    id: str
    name: str = ""
    stream_id: str = ""        # Current source ID
    muted: bool = False
    client_ids: list[str] = field(default_factory=list)

    @property
    def volume(self) -> int:
        """Average volume of connected clients."""
        if not self.client_ids:
            return 0
        # Computed from StateStore's clients
        return 0  # Placeholder
```

### Source (Stream)

```python
@dataclass
class Source:
    """An audio source/stream."""
    id: str
    name: str = ""
    status: str = "idle"       # idle, playing
    stream_type: str = ""      # spotify, airplay, etc.

    @property
    def is_playing(self) -> bool:
        return self.status == "playing"
```

### ServerState

```python
@dataclass
class ServerState:
    """Complete snapshot of server state."""
    server: Server
    groups: list[Group] = field(default_factory=list)
    clients: list[Client] = field(default_factory=list)
    sources: list[Source] = field(default_factory=list)
    connected: bool = False
    version: str = ""
    host: str = ""
    mac: str = ""
```

---

## JSON-RPC Mapping

| Snapcast Response | Model |
|-------------------|-------|
| `server` | `Server` |
| `clients[]` | `Client[]` |
| `groups[]` | `Group[]` |
| `streams[]` (sources) | `Source[]` |

---

*Next: [UI/UX Design](docs/04-UI-UX.md) →*
