# SnapCTRL - Testing Strategy

## Coverage Target: 85% (aspirational, not enforced in CI)

### Test Pyramid

```
        ┌─────────┐
        │   E2E   │  5%  (manual)
       ┌┴────────┴┐
       │  UI Tests │ 20% (pytest-qt)
      ┌┴──────────┴┐
      │ Integration│ 25% (mocked TCP)
     ┌┴────────────┴┐
     │   Unit Tests  │ 50% (pure functions)
    └────────────────┘
```

## Current Test Count: 401 tests

## Unit Tests (50%)

| Module | Tests | Focus |
|--------|-------|-------|
| `models/` | Model creation, properties, validation, edge cases | 90% |
| `core/state.py` | State updates, signal emission, optimistic updates | 90% |
| `core/config.py` | Load/save, QSettings mock | 85% |
| `api/client.py` | RPC methods, state parsing, set_client_* methods | 85% |
| `api/mpd/` | MPD protocol parsing, client methods, album art retrieval | 85% |
| `api/album_art/` | iTunes/MusicBrainz providers, fallback chain | 80% |
| `core/ping.py` | Cross-platform ping, RTT formatting, color coding | 80% |
| `core/discovery.py` | mDNS service parsing | 80% |

## Integration Tests (25%)

| Scenario | Test |
|----------|------|
| Connect → GetStatus → Parse | Mock TCP server |
| Volume change → RPC call | Verify request format |
| Reconnection on drop | Simulate TCP disconnect |
| State updates → UI signals | Connect state to test receiver |
| MPD metadata → Source update | Monitor integration |

## UI Tests (20%)

| Component | Tests |
|-----------|-------|
| MainWindow | Create, show, close |
| VolumeSlider | Drag, mute button, value display |
| GroupCard | Render with data, context menus, source dropdown |
| ClientCard | Render, context menus, rename signal |
| SourcesPanel | Set sources, playing indicator, clear |
| GroupsPanel | Set groups, update, clear, rename signals |
| PropertiesPanel | Group/client/source display, latency spinbox, clear |
| ThemeManager | Palette creation, dark/light detection |
| SystemTrayManager | Tray creation, menu building, state updates |

## E2E Tests (5%)

Manual checklist:
- [ ] Launch app → connect to real server (mDNS or manual)
- [ ] Change volume → verify audio changes
- [ ] Switch source → verify groups update
- [ ] Disconnect → reconnect automatically
- [ ] Select client → adjust latency → verify sync change
- [ ] Right-click → rename client/group
- [ ] Toggle macOS dark/light mode → verify theme switches
- [ ] Close window → verify tray icon persists → restore window
- [ ] Verify now playing metadata updates on track change

## Test Fixtures

```python
# tests/conftest.py
@pytest.fixture
def mock_server():
    """Mock Snapcast server with test data."""
    return {
        "server": {"version": "0.27.0"},
        "groups": [...],
        "clients": [...],
        "streams": [...],
    }

@pytest.fixture
def state_store(qtbot):
    """StateStore for signal testing."""
    store = StateStore()
    qtbot.addWidget(store)  # Not a widget, but registers for cleanup
    return store
```

---

*Next: [Work Breakdown Structure](docs/08-WBS.md) →*

*Last updated: 2026-01-29*
