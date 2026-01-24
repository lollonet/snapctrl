# Snapcast MVP - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         Snapcast MVP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────┐    │
│  │   UI Layer  │◄───│ State Store  │◄───│  API Client     │    │
│  │  (PySide6)  │    │  (Signals)   │    │  (WebSocket)    │    │
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
| **Networking** | websockets + asyncio | Async WebSocket, JSON-RPC protocol |
| **Threading** | QThread + asyncio | Non-blocking WebSocket in Qt app |
| **State** | Central state + Qt signals | Simple, effective, debuggable |
| **Config** | QSettings | Native to Qt, cross-platform storage |
| **Testing** | pytest + pytest-qt | Industry standard, Qt widget support |
| **CI/CD** | GitHub Actions | Git integration, free for public |
| **Packaging** | PyInstaller (Win), briefcase (macOS/AppImage) | Cross-platform binaries |

---

## Module Structure

```
src/snapcast_mvp/
├── __init__.py
├── __main__.py              # Entry point
├── main.py                  # Application bootstrap
│
├── core/                    # Business logic (no Qt)
│   ├── __init__.py
│   ├── state.py             # StateStore, state models
│   ├── api.py               # SnapcastClient (WebSocket)
│   └── config.py            # ConfigManager (QSettings wrapper)
│
├── ui/                      # Qt UI layer
│   ├── __init__.py
│   ├── main_window.py       # MainWindow
│   ├── panels/              # UI panels
│   │   ├── __init__.py
│   │   ├── sources.py       # SourcesPanel (left)
│   │   ├── groups.py        # GroupsPanel (center)
│   │   └── properties.py    # PropertiesPanel (right)
│   ├── widgets/             # Reusable widgets
│   │   ├── __init__.py
│   │   ├── volume_slider.py # VolumeSlider with mute
│   │   ├── group_card.py    # GroupCard widget
│   │   └── status_indicator.py # Connection status
│   ├── dialogs/             # Modal dialogs
│   │   ├── __init__.py
│   │   └── connection.py    # ConnectionDialog
│   └── resources/           # Icons, assets
│       └── qrc_resources.py
│
└── models/                  # Data models (pure Python)
    ├── __init__.py
    ├── server.py            # Server, ServerProfile
    ├── client.py            # Client, ClientState
    ├── group.py             # Group, GroupState
    └── source.py            # Source, StreamState
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
    groups_changed = Signal(list[Group])
    clients_changed = Signal(list[Client])
    sources_changed = Signal(list[Source])

    def __init__(self):
        super().__init__()
        self._groups: dict[str, Group] = {}
        self._clients: dict[str, Client] = {}
        self._sources: dict[str, Source] = {}

    def update_from_status(self, status: dict) -> None:
        """Update state from server status, emit signals."""
        # ... update internal state
        self.groups_changed.emit(list(self._groups.values()))
```

**UI widgets connect to signals:**
```python
self._state.groups_changed.connect(self._on_groups_updated)
```

### 2. Async WebSocket in Qt App

```python
class WebSocketWorker(QThread):
    """Background thread running asyncio WebSocket."""

    data_received = Signal(dict)
    connection_lost = Signal()

    def __init__(self, url: str):
        super().__init__()
        self._url = url
        self._loop: asyncio.AbstractEventLoop | None = None

    def run(self) -> None:
        """Run asyncio event loop in this thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._connect())

    async def _connect(self) -> None:
        async with websockets.connect(self._url) as ws:
            while True:
                data = await ws.recv()
                self.data_received.emit(json.loads(data))
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
  ├─> Create WebSocketWorker
  ├─> Create MainWindow
  │    ├─> SourcesPanel (subscribes to state.sources_changed)
  │    ├─> GroupsPanel (subscribes to state.groups_changed)
  │    └─> PropertiesPanel (subscribes to selection)
  ├─> Connect to last server (if auto-connect enabled)
  └─> app.exec()
```

### 2. Server Connection

```
User: Click "Connect"
  └─> MainWindow._on_connect()
       └─> WebSocketWorker.start()
            ├─> Connect to ws://host:1704/jsonrpc
            ├─> Send: {"id": 1, "method": "Server.GetStatus"}
            └─> Receive status
                 └─> StateStore.update_from_status()
                      └─> Emit signals
                           └─> UI widgets update
```

### 3. Volume Change

```
User: Drag volume slider
  └─> VolumeSlider.valueChanged
       └─> GroupsPanel._on_volume_changed(group_id, value)
            └─> WebSocketWorker.send_rpc({
                   "method": "Client.SetVolume",
                   "params": {"id": client_id, "volume": {"percent": value}}
                 })
                 └─> Server confirms
                      └─> StateStore.update_client_volume()
                           └─> UI slider updates (optimistic)
```

---

## Threading Model

| Thread | Responsibility | Communication |
|--------|----------------|---------------|
| **Main (Qt)** | UI rendering, event handling | Signals → Worker |
| **Worker (QThread)** | WebSocket I/O, asyncio loop | Signals → Main |

**Rule:** No Qt widgets in Worker thread. No blocking I/O in Main thread.

---

## Error Handling Strategy

| Error Type | Handling | User Feedback |
|------------|----------|---------------|
| Connection refused | Retry 5x with exponential backoff | "Could not connect. Retrying..." |
| WebSocket dropped | Auto-reconnect | Status indicator: yellow |
| Invalid RPC response | Log, show error in status bar | "Server returned invalid data" |
| Config corrupted | Reset to defaults | "Settings reset to defaults" |

---

## Quality Gates

```yaml
# CONTROL.yaml
project:
  name: snapcast-mvp
  language: python
  ci_platform: github

quality:
  paths: ["src", "tests"]
  coverage:
    enforce: true
    line: 85
    branch: 75
  complexity:
    enforce: true
    mccabe:
      warn: 8
      fail: 12
```

---

## Security Considerations

1. **Local network only** - No internet connectivity
2. **No authentication** - Snapcast JSON-RPC has no auth (trusting network)
3. **Input validation** - Validate host, port from user input
4. **WebSocket origin** - Verify server response format

---

*Next: [Data Models](docs/03-DATA-MODELS.md) →*
