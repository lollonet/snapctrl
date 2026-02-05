# SnapCTRL

> Native desktop controller for Snapcast multi-room audio systems.

[![SnapForge](https://img.shields.io/badge/part%20of-SnapForge-blue)](https://github.com/lollonet/snapforge)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Qt](https://img.shields.io/badge/Qt-6.8+-green.svg)](https://www.qt.io/)
[![CI](https://github.com/lollonet/snapctrl/actions/workflows/ci.yml/badge.svg)](https://github.com/lollonet/snapctrl/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

## Overview

SnapCTRL is a cross-platform desktop application that provides an intuitive GUI for controlling Snapcast servers. Built with Python and PySide6 (Qt6), it connects to your Snapcast server via TCP and allows real-time control of groups, clients, and audio sources.

### Features

- **Connection Management**: Connect to any Snapcast server via TCP (port 1705)
- **mDNS Autodiscovery**: Automatic server detection on local network via zeroconf
- **Real-time State**: Live updates from server via JSON-RPC over TCP
- **Group Control**: Volume, mute, and stream selection per group
- **Client Control**: Individual volume and mute for each client
- **Per-Client Latency**: Interactive latency adjustment for connected clients
- **Context Menus & Rename**: Right-click to rename clients and groups
- **Now Playing Metadata**: Track title, artist, album from Snapcast streams
- **MPD Integration**: Track metadata and album art via MPD protocol
- **Album Art**: Fallback chain — MPD → iTunes → MusicBrainz
- **System Tray**: Minimize-to-tray with quick volume sliders
- **Dark/Light Theme**: Automatic system theme detection and runtime switching
- **Auto-Reconnection**: Exponential backoff (2s–30s), infinite retry
- **Server-Side Jitter Stats**: Median/P95 jitter via `Client.GetTimeStats` (with ping fallback)
- **Server Version**: Snapserver version displayed in status bar alongside RTT
- **Resizable Album Art**: Cover art fills available panel width, scales on resize
- **Cross-Platform Builds**: PyInstaller packaging for macOS, Windows, Linux

### Current Status

| Component        | Status       |
| ---------------- | ------------ |
| Data Models      | ✅ Complete   |
| TCP API Client   | ✅ Complete   |
| State Management | ✅ Complete   |
| UI Widgets       | ✅ Complete   |
| UI Panels        | ✅ Complete   |
| MPD Integration  | ✅ Complete   |
| Album Art        | ✅ Complete   |
| Integration      | ✅ Complete   |

Run `pytest tests/ -v` for current test count (934 tests).

## Requirements

- Python 3.11+
- PySide6 6.8+
- zeroconf (for mDNS autodiscovery)
- A running Snapcast server (v0.27+ tested, v0.34+ for jitter stats)

## Installation

```bash
# Clone the repository
git clone https://github.com/lollonet/snapctrl.git
cd snapctrl

# Install with uv (recommended)
uv sync

# Or with pip
pip install -e .
```

## Usage

```bash
# Run the application (after pip install)
snapctrl

# Or run as Python module
python -m snapctrl
```

Set environment variable for headless Qt (useful for testing):

```bash
export QT_QPA_PLATFORM=offscreen
```

## Development

```bash
# Install development dependencies
uv sync

# Run quality checks
uv run ruff check src tests
uv run ruff format --check src tests

# Run tests (requires Qt display or QT_QPA_PLATFORM=offscreen)
QT_QPA_PLATFORM=offscreen uv run pytest tests/ -v

# Type checking (manual)
uv run basedpyright src/
```

### Test Coverage (934 tests)

- **Models, protocol, API**: 150+ tests
- **Core (state, config, ping, discovery)**: 80+ tests
- **UI tests**: 100+ tests (widgets, panels, tray, theme)
- **Integration tests**: 30+ tests
- **Live server tests**: 20+ tests
- **MPD/album art tests**: 17+ tests

## Architecture

- **Models**: Frozen dataclasses for immutable state (Client, Group, Server, Source, ServerProfile)
- **API**: Asyncio TCP client with JSON-RPC 2.0, MPD protocol client, album art provider chain
- **Core**: StateStore with Qt signals, QThread worker, mDNS discovery, ping monitor, MPD monitor
- **UI**: PySide6 tri-pane layout, system tray, dark/light theme auto-detection

See [docs/02-ARCHITECTURE.md](docs/02-ARCHITECTURE.md) for details.

## Roadmap

- [x] Month 1: Foundation (Models, API, State, Configuration)
- [x] Month 2: UI Foundation (Widgets, Panels, MainWindow)
- [x] Month 2: Advanced UI (Context menus, rename, latency, MPD, tray, theme)
- [ ] Month 3: Polish (Drag & drop, settings dialog, keyboard shortcuts)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Code must pass:

- `ruff check` - linting
- `ruff format` - formatting
- `pytest` - tests

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [Snapcast](https://github.com/badaix/snapcast) - Multi-room audio system
- [PySide6](https://pypi.org/project/PySide6/) - Qt6 Python bindings
