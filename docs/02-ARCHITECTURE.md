# Snapcast MVP - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Snapcast MVP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │   UI Layer  │◄───│ State Store  │◄───│  API Client     │    │
│  │  (PySide6)  │    │  (Signals)   │    │  (asyncio TCP)  │    │
│  └─────────────┘    └──────────────┘    └────────┬────────┘    │
│                                                      │             │
│                                                  ┌───▼────┐       │
│                                                  │Snapcast│       │
│                                                  │ Server │       │
│                                                  └────────┘       │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **UI Framework** | PySide6 (Qt6) | Cross-platform, native feel, Python |
| **Networking** | asyncio + TCP sockets | Native async I/O, JSON-RPC protocol |
| **Threading** | QThread + asyncio | Non-blocking TCP in Qt app |
| **State** | Central state + Qt signals | Simple, effective, debuggable |
| **Config** | QSettings | Native to Qt, cross-platform storage |
| **Testing** | pytest + pytest-qt | Industry standard, Qt widget support |
| **CI/CD** | GitHub Actions | Git integration, free for public |
| **Packaging** | PyInstaller (Win), briefcase (macOS/AppImage) | Cross-platform binaries |

**Note:** Snapcast uses raw TCP sockets (not WebSocket) for JSON-RPC on port 1705.

---

## Module Structure

```
src/snapcast_mvp/
├── __init__.py
├── __main__.py              # Entry point
│
├── models/                  # Data models (frozen dataclasses)
│   ├── __init__.py
│   ├── server.py            # Server, ServerProfile
│   ├── client.py            # Client
│   ├── group.py             # Group
│   ├── source.py            # Source
│   ├── profile.py           # ServerProfile
│   └── server_state.py      # ServerState aggregate
│
├── api/                     # API layer
│   ├── __init__.py
│   ├── client.py            # SnapcastClient (asyncio TCP)
│   └── protocol.py          # JSON-RPC types
│
├── core/                    # Business logic
│   ├── __init__.py
│   ├── state.py             # StateStore (Qt signals)
│   ├── worker.py            # SnapcastWorker (QThread)
│   ├── config.py            # ConfigManager (QSettings wrapper)
│   └── controller.py        # Controller (UI → API bridge)
│
└── ui/                      # Qt UI layer
    ├── __init__.py
    ├── main_window.py       # MainWindow
    ├── panels/              # UI panels
    │   ├── __init__.py
    │   ├── sources.py       # SourcesPanel (left)
    │   ├── groups.py        # GroupsPanel (center)
    │   └── properties.py    # PropertiesPanel (right)
    └── widgets/             # Reusable widgets
        ├── __init__.py
        ├── volume_slider.py # VolumeSlider with mute
        ├── group_card.py    # GroupCard widget
        └── client_card.py   # ClientCard widget
```

---

## Architecture Patterns

### 1. State Management (Central Store + Signals)

```python
class StateStore(QObject):
    """Central state store emitting Qt signals on changes."""

    # Signals
    server_connected = Signal()
    server_disconnected = Signal()
    state_changed = Signal(ServerState)

    def __init__(self):
        super().__init__()
        self._state: ServerState | None = None

    def update_from_server_state(self, state: ServerState) -> None:
        """Update state from server, emit signal."""
        self._state = state
        self.state_changed.emit(state)
```

**UI widgets connect to signals:**
```python
self._state.state_changed.connect(self._on_state_updated)
```

### 2. Async TCP in Qt App

```python
class SnapcastWorker(QThread):
    """Background thread running asyncio TCP client."""

    state_received = Signal(ServerState)
    connection_lost = Signal()

    def __init__(self, host: str, port: int):
        super().__init__()
        self._host = host
        self._port = port
        self._loop: asyncio.AbstractEventLoop | None = None
        self._client: SnapcastClient | None = None

    def run(self) -> None:
        """Run asyncio event loop in this thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect())

    async def _connect(self) -> None:
        """Connect to Snapcast server and listen for updates."""
        self._client = SnapcastClient(self._host, self._port)
        async for state in self._client.stream():
            self.state_received.emit(state)
```

### 3. Configuration Persistence (QSettings)

```python
class ConfigManager:
    """Wrapper around QSettings for type-safe config access."""

    def __init__(self):
        self._settings = QSettings("SnapcastMVP", "Snapcast Controller")

    def get_server_profiles(self) -> list[ServerProfile]:
        """Load saved server profiles."""
        data = self._settings.value("servers", [], list)
        return [ServerProfile.from_dict(d) for d in data]

    def save_server_profiles(self, profiles: list[ServerProfile]) -> None:
        """Persist server profiles."""
        data = [p.to_dict() for p in profiles]
        self._settings.setValue("servers", data)
```

---

## Data Flow

### 1. Application Startup

```
main()
  ├─> Load config (QSettings)
  ├─> Create StateStore
  ├─> Create SnapcastWorker (QThread)
  ├─> Create MainWindow
  │    ├─> SourcesPanel (subscribes to state)
  │    ├─> GroupsPanel (subscribes to state)
  │    └─> PropertiesPanel (subscribes to selection)
  ├─> Connect to last server (if auto-connect enabled)
  └─> app.exec()
```

### 2. Server Connection

```
User: Click "Connect"
  └─> MainWindow._on_connect()
       └─> SnapcastWorker.start()
            ├─> Connect to tcp://host:1705
            ├─> Send: {"id": 1, "method": "Server.GetStatus"}
            └─> Receive status
                 └─> StateStore.update_from_server_state()
                      └─> Emit state_changed signal
                           └─> UI widgets update
```

### 3. Volume Change

```
User: Drag volume slider
  └─> VolumeSlider.valueChanged
       └─> GroupsPanel._on_volume_changed(group_id, value)
            └─> Controller.set_client_volume()
                 └─> SnapcastClient.set_client_volume()
                      └─> Send RPC: {"method": "Client.SetVolume", ...}
                           └─> Server confirms
                                └─> StateStore updates
                                     └─> UI slider updates (optimistic)
```

---

## Threading Model

| Thread | Responsibility | Communication |
|--------|----------------|---------------|
| **Main (Qt)** | UI rendering, event handling | Signals → Worker |
| **Worker (QThread)** | TCP I/O, asyncio loop | Signals → Main |

**Rule:** No Qt widgets in Worker thread. No blocking I/O in Main thread.

---

## Error Handling Strategy

| Error Type | Handling | User Feedback |
|------------|----------|---------------|
| Connection refused | Retry 5x with exponential backoff | "Could not connect. Retrying..." |
| TCP connection dropped | Auto-reconnect | Status indicator: yellow |
| Invalid RPC response | Log, show error in status bar | "Server returned invalid data" |
| Config corrupted | Reset to defaults | "Settings reset to defaults" |

---

## Quality Gates

```bash
# Pre-commit (automatic)
uv run ruff check --fix      # linting
uv run ruff format           # formatting

# Manual (before major commits)
uv run basedpyright src/     # type checking
QT_QPA_PLATFORM=offscreen uv run pytest  # tests
```

**CI (GitHub Actions):**
- Runs: ruff check, ruff format, pytest (unit + integration only)
- Skips: UI tests (no Qt in CI), integration tests (no live server)

---

## Security Considerations

1. **Local network only** - No internet connectivity
2. **No authentication** - Snapcast JSON-RPC has no auth (trusting network)
3. **Input validation** - Validate host, port from user input
4. **TCP connection** - Verify server response format (JSON-RPC)

---

*Next: [Data Models](03-DATA-MODELS.md) →*

*Last updated: 2025-01-26*
