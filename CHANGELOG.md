# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Week 1: Data Models** - Jan 24
  - Immutable frozen dataclasses for Client, Group, Server, Source
  - ServerState aggregate with lookup methods (get_client, get_group, get_source)
  - Full type hints with basedpyright strict mode compliance
  - 100% test coverage on all models

- **Week 2: TCP API Client** - Jan 24
  - SnapcastClient using asyncio TCP sockets (Snapcast uses raw TCP on port 1705)
  - JSON-RPC 2.0 protocol implementation with request/response handling
  - Automatic reconnection with exponential backoff (max 30s delay)
  - Real server integration validated against Snapcast v0.34.0 at 192.168.63.3
  - Methods: get_status, set_client_volume, set_group_mute, set_group_stream

- **Week 3: State Management** - Jan 25
  - StateStore with Qt signals for reactive UI updates
  - SnapcastWorker QThread for running async client in background
  - Thread-safe state updates with optimistic UI support
  - Integration with Qt's signal/slot mechanism

- **Week 4: Configuration** - Jan 25
  - ServerProfile dataclass for connection configuration
  - ConfigManager (QSettings wrapper) for persistent storage
  - Server profile CRUD operations (add, remove, get, list)
  - Auto-connect profile selection
  - Last-connected server tracking

- **Week 5-6: Core UI Widgets** - Jan 26
  - VolumeSlider widget with mute toggle and volume percentage display
  - GroupCard widget with expand/collapse for client list
  - Qt signal/slot integration for reactive updates
  - Styled components matching dark theme

- **Week 7-8: UI Panels & MainWindow** - Jan 26
  - MainWindow with tri-pane layout (Sources, Groups, Properties)
  - SourcesPanel for audio source selection
  - GroupsPanel for scrollable group cards
  - PropertiesPanel for selected item details
  - Connected to StateStore for live updates

- **Week 9: Client Controls** - Jan 26
  - ClientCard widget for individual client control
  - Volume and mute controls per client
  - Connection status indicator
  - Signal wiring to Controller for API calls

- **GitHub-Native Claude Review CI** - Jan 26
  - Integrated anthropic-actions/claude-review@v0.3.0
  - Uses GitHub OIDC authentication (no API keys required)
  - Automatic code review on pull requests

### Fixed
- **Encapsulation Violations** ([#1](https://github.com/lollonet/snapcast-mvp/pull/1)) - Jan 26
  - Added public APIs to GroupCard: `set_selected()`, `update_clients()`, `set_mute_state()`
  - Added public API to SnapcastClient: `set_event_handlers()`
  - GroupsPanel now uses GroupCard public APIs instead of private members
  - Worker now uses SnapcastClient public API

- **Server Model** - Jan 26
  - Port: 1704 → 1705 (correct Snapserver default port)
  - Protocol documentation: WebSocket → Raw TCP JSON-RPC
  - Tests updated to match corrected values

### Changed
- **CI Configuration** - Jan 26
  - Skip UI tests in CI (Qt GUI libraries unavailable in GitHub Actions)
  - Skip integration tests in CI (require live Snapserver)
  - Added pytest-asyncio for async test support
  - Removed coverage threshold (artificially low without UI tests)
  - Renamed test_client_card.py → test_ui_client_card.py for consistency

### Infrastructure
- Partial BassCodeBase adoption (CLI tooling only, no git hooks)
- GitHub Actions CI pipeline with uv
- Quality gates: ruff, ruff format, pytest (unit + integration)
- 225 tests passing (127 unit + 20 week3 integration + 58 UI + 20 live server)

## [0.1.0] - 2025-01-24

### Added
- Initial project scaffold with BassCodeBase export
- Data models (Server, Client, Group, Source, ServerState)
- TCP API client with JSON-RPC protocol
- Foundation: Month 1 complete (Weeks 1-4)
