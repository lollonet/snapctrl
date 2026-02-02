# SnapCTRL - Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         SnapCTRL                            │
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
| **Discovery** | zeroconf | mDNS autodiscovery on LAN |
| **Packaging** | PyInstaller | Cross-platform binaries (all platforms) |

**Note:** Snapcast uses raw TCP sockets (not WebSocket) for JSON-RPC on port 1705.

---

## Module Structure

```
src/snapctrl/
├── __init__.py
├── __main__.py              # Entry point, signal wiring, mDNS bootstrap
│
├── models/                  # Data models (frozen dataclasses)
│   ├── __init__.py
│   ├── server.py            # Server
│   ├── client.py            # Client (19 fields)
│   ├── group.py             # Group
│   ├── source.py            # Source, SourceStatus enum
│   ├── profile.py           # ServerProfile (with ID generation)
│   └── server_state.py      # ServerState aggregate
│
├── api/                     # API layer
│   ├── __init__.py
│   ├── client.py            # SnapcastClient (asyncio TCP, JSON-RPC)
│   ├── protocol.py          # JSON-RPC request/response/notification types
│   ├── mpd/                 # MPD client module
│   │   ├── __init__.py
│   │   ├── client.py        # MpdClient (asyncio TCP)
│   │   ├── protocol.py      # MPD protocol parsing
│   │   └── types.py         # MpdTrack, MpdStatus, MpdAlbumArt
│   └── album_art/           # Album art provider chain
│       ├── __init__.py
│       ├── provider.py      # AlbumArtProvider base, FallbackAlbumArtProvider
│       ├── itunes.py        # ITunesAlbumArtProvider
│       └── musicbrainz.py   # MusicBrainzAlbumArtProvider
│
├── core/                    # Business logic
│   ├── __init__.py
│   ├── state.py             # StateStore (Qt signals, optimistic updates)
│   ├── worker.py            # SnapcastWorker (QThread, 14 public methods)
│   ├── config.py            # ConfigManager (QSettings wrapper)
│   ├── controller.py        # Controller (UI → API bridge)
│   ├── discovery.py         # mDNS autodiscovery (zeroconf)
│   ├── ping.py              # Network RTT ping (cross-platform)
│   ├── mpd_monitor.py       # MPD metadata polling + art cache
│   └── snapclient_manager.py # Local snapclient process lifecycle
│
└── ui/                      # Qt UI layer
    ├── __init__.py
    ├── main_window.py       # MainWindow (tri-pane + toolbar)
    ├── theme.py             # ThemeManager, ThemePalette (dark/light)
    ├── system_tray.py       # SystemTrayManager (tray icon + menu)
    ├── panels/              # UI panels
    │   ├── __init__.py
    │   ├── sources.py       # SourcesPanel (left)
    │   ├── groups.py        # GroupsPanel (center)
    │   └── properties.py    # PropertiesPanel (right, latency spinbox)
    └── widgets/             # Reusable widgets
        ├── __init__.py
        ├── volume_slider.py # VolumeSlider with mute
        ├── group_card.py    # GroupCard (context menus, source dropdown)
        └── client_card.py   # ClientCard (context menus, rename)
```

---

## Architecture Patterns

### 1. State Management (Central Store + Signals)

```python
class StateStore(QObject):
    """Central state store emitting Qt signals on changes."""

    # Signals
    connection_changed = Signal(bool)     # True=connected, False=disconnected
    groups_changed = Signal(list)         # list[Group]
    clients_changed = Signal(list)        # list[Client]
    sources_changed = Signal(list)        # list[Source]
    state_changed = Signal(object)        # ServerState

    def __init__(self):
        super().__init__()
        self._state: ServerState | None = None

    def update_from_server_state(self, state: ServerState) -> None:
        """Update state from server, emit granular signals."""
        self._state = state
        self.state_changed.emit(state)
        self.groups_changed.emit(list(state.groups))
        self.clients_changed.emit(list(state.clients))
        self.sources_changed.emit(list(state.sources))
```

**UI widgets connect to signals:**
```python
self._state.state_changed.connect(self._on_state_updated)
```

### 2. Async TCP in Qt App

```python
class SnapcastWorker(QThread):
    """Background thread running asyncio TCP client."""

    connected = Signal()
    disconnected = Signal()
    connection_lost = Signal()
    state_received = Signal(object)      # ServerState
    error_occurred = Signal(object)      # Exception

    def run(self) -> None:
        """Run asyncio event loop in this thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        self._loop.run_until_complete(self._run_loop())

    # Thread-safe public API (called from Main thread):
    def set_client_volume(self, client_id: str, volume: int) -> None:
        """Schedule volume change on the worker's event loop."""
        if self._loop and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_set_client_volume(client_id, volume), self._loop
            )
```

### 3. Configuration Persistence (QSettings)

```python
class ConfigManager:
    """Wrapper around QSettings for type-safe config access."""

    def __init__(self):
        self._settings = QSettings("SnapCTRL", "SnapCTRL")

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
  ├─> Apply ThemeManager (dark/light auto-detection)
  ├─> Discover server via mDNS (or use CLI args)
  ├─> Create StateStore
  ├─> Create SnapcastWorker (QThread) → connect + fetch status
  ├─> Create MainWindow
  │    ├─> SourcesPanel (subscribes to state)
  │    ├─> GroupsPanel (subscribes to state)
  │    └─> PropertiesPanel (subscribes to selection)
  ├─> Create SystemTrayManager (tray icon + menu)
  ├─> Start MpdMonitor (track metadata + album art polling)
  ├─> Start PingMonitor (network RTT, 15s interval)
  ├─> Wire all signals (state → UI, worker → state)
  └─> app.exec()
```

### 2. Server Connection

```
Startup: mDNS autodiscovery OR CLI host:port
  └─> SnapcastWorker.start()
       └─> asyncio event loop in QThread
            ├─> Connect to tcp://host:1705
            ├─> Send: {"id": 1, "method": "Server.GetStatus"}
            └─> Receive status → parse → emit state_received
                 └─> StateStore.update_from_server_state()
                      └─> Emit granular signals (groups, clients, sources)
                           └─> UI widgets update
```

### 3. Volume Change

```
User: Drag volume slider
  └─> VolumeSlider.valueChanged
       └─> Worker.set_client_volume(client_id, volume)
            └─> asyncio.run_coroutine_threadsafe(...)
                 └─> SnapcastClient.set_client_volume()
                      └─> Send RPC: {"method": "Client.SetVolume", ...}
                           └─> _fetch_status() → StateStore updates
                                └─> UI slider updates
```

---

## Threading Model

| Thread | Responsibility | Communication |
|--------|----------------|---------------|
| **Main (Qt)** | UI rendering, event handling | Signals → Worker |
| **Worker (QThread)** | TCP I/O, asyncio loop | Signals → Main |
| **PingMonitor** | Background RTT measurement (15s) | Callback → Main |
| **MpdMonitor** | MPD polling, album art fetch | Signals → Main |
| **SnapclientManager** | Local snapclient process lifecycle | Signals → Main |
| **AlbumArt (daemon)** | Fallback art fetch (iTunes/MusicBrainz) | QTimer.singleShot → Main |

**Rule:** No Qt widgets in Worker thread. No blocking I/O in Main thread.

---

## Error Handling Strategy

| Error Type | Handling | User Feedback |
|------------|----------|---------------|
| Connection refused | Exponential backoff (2s→30s), infinite retry | Toolbar indicator: red dot |
| TCP connection dropped | Auto-reconnect with backoff | Toolbar indicator: red dot |
| Invalid RPC response | Log, show error in status bar | "Server returned invalid data" |
| Config corrupted | Reset to defaults | "Settings reset to defaults" |

---

## Quality Gates

```bash
# Pre-commit (automatic)
uv run ruff check --fix      # linting
uv run ruff format           # formatting

# Manual (before major commits)
uv run basedpyright src/ bin/ tests/  # type checking
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

*Last updated: 2026-02-02*
