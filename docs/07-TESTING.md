# SnapCTRL - Testing Strategy

## Coverage Target: 85%

### Test Pyramid

```
        ┌─────────┐
        │   E2E   │  5%  (manual)
       ┌┴────────┴┐
       │  UI Tests │ 20% (pytest-qt)
      ┌┴──────────┴┐
      │ Integration│ 25% (mocked WebSocket)
     ┌┴────────────┴┐
     │   Unit Tests  │ 50% (pure functions)
    └────────────────┘
```

## Unit Tests (50%)

| Module | Tests | Coverage |
|--------|-------|----------|
| `models/` | Dataclass creation, properties, validation | 90% |
| `core/state.py` | State updates, signal emission | 90% |
| `core/config.py` | Load/save, QSettings mock | 85% |
| `core/api.py` | RPC methods, state parsing (mocked ws) | 85% |

## Integration Tests (25%)

| Scenario | Test |
|----------|------|
| Connect → GetStatus → Parse | Mock WebSocket server |
| Volume change → RPC call | Verify request format |
| Reconnection on drop | Simulate WebSocket close |
| State updates → UI signals | Connect state to test receiver |

## UI Tests (20%)

| Component | Tests |
|-----------|-------|
| MainWindow | Create, show, close |
| VolumeSlider | Drag, mute button, value display |
| GroupCard | Render with data, click handlers |
| ConnectionDialog | Form validation, save button |

## E2E Tests (5%)

Manual checklist:
- [ ] Launch app → connect to real server
- [ ] Change volume → verify audio changes
- [ ] Switch source → verify groups update
- [ ] Disconnect → reconnect automatically

## Test Fixtures

```python
# tests/conftest.py
@pytest.fixture
def mock_server():
    """Mock Snapcast server with test data."""
    return {
        "server": {"version": "0.26.0"},
        "groups": [...],
        "clients": [...],
        "streams": [...],
    }

@pytest.fixture
def qt_app():
    """Qt application for UI tests."""
    return QApplication([])

@pytest.fixture
def state_store():
    """StateStore with no Qt dependencies."""
    return StateStore()
```

## Mock WebSocket

```python
# tests/helpers/mock_server.py
class MockSnapcastServer:
    """In-process WebSocket server for testing."""

    async def handle(self, websocket):
        async for message in websocket:
            request = json.loads(message)
            response = self._dispatch(request["method"])
            await websocket.send(json.dumps(response))
```

---

*Next: [Work Breakdown Structure](docs/08-WBS.md) →*
