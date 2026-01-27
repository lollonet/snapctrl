# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Mute-Only API** ([#2](https://github.com/lollonet/snapcast-mvp/pull/2)) - Jan 27
  - `set_client_mute()` method for mute operations without volume data
  - Prevents duplicate API calls when toggling mute
  - CLI entry point with host/port argument parsing

- **mDNS Autodiscovery** ([#3](https://github.com/lollonet/snapcast-mvp/pull/3)) - Jan 27
  - Automatic Snapcast server discovery on local network
  - Zero-configuration startup when no arguments provided
  - Shows FQDN and IP in window title (e.g., "raspy.local (192.168.63.3)")

- **Source Details Panel** ([#5](https://github.com/lollonet/snapcast-mvp/pull/5)) - Jan 27
  - Status indicator (Playing/Idle) with color coding
  - Stream type, codec, and sample format display
  - Human-readable format (e.g., "48kHz/16bit/stereo")

- **Enhanced Client Properties** ([#5](https://github.com/lollonet/snapcast-mvp/pull/5)) - Jan 27
  - System info (OS and architecture)
  - Last seen timestamp with human-readable format
  - Network RTT ping measurement (updated every 15 seconds)
  - Color-coded latency: green (<50ms), yellow (50-100ms), red (>100ms)

- **Cross-Platform Build Configuration** - Jan 27
  - PyInstaller spec files for macOS, Windows, and Linux
  - Automated build script (`scripts/build.py`)
  - Windows .ico icon (multi-resolution)
  - macOS .app bundle with .dmg packaging

- **App Branding** - Jan 27
  - Renamed from "Snapcast MVP" to "SnapCTRL"
  - Custom app icon (SVG, ICNS, ICO)
  - macOS app bundle with proper Info.plist

### Fixed

- **Source Selection** ([#4](https://github.com/lollonet/snapcast-mvp/pull/4)) - Jan 27
  - Dropdown now correctly changes stream on server
  - Fixed API parameter naming (`stream_id` instead of `streamId`)

- **Group Volume Sync** ([#4](https://github.com/lollonet/snapcast-mvp/pull/4)) - Jan 27
  - Slider shows actual average volume (not fixed 50%)
  - Client sliders follow group slider visually
  - Syncs with external changes (mobile app) after 1s inactivity
  - Auto-mute when volume reaches 0

- **Signal Handling** ([#2](https://github.com/lollonet/snapcast-mvp/pull/2)) - Jan 27
  - Fixed VolumeSlider signal cascading on mute toggle
  - Blocks signals during programmatic updates

- **Connection Status** ([#4](https://github.com/lollonet/snapcast-mvp/pull/4)) - Jan 27
  - Green/red color indicators for connected/disconnected
  - Properties panel updates when client selected

### Changed

- **TCP Buffer Size** - Jan 27
  - Increased to 1MB for large Server.GetStatus responses

- **Platform-Specific Ping** - Jan 27
  - macOS: `-W` timeout in milliseconds
  - Linux: `-W` timeout in seconds
  - Windows: `-w` timeout in milliseconds

## [0.1.0-alpha] - 2026-01-26

### Added

- **Core Architecture** (Weeks 1-4)
  - Immutable frozen dataclasses for Client, Group, Server, Source
  - TCP API client with JSON-RPC 2.0 protocol
  - StateStore with Qt signals for reactive updates
  - SnapcastWorker QThread for async operations
  - ConfigManager for persistent settings

- **UI Foundation** (Weeks 5-9)
  - MainWindow with tri-pane layout
  - VolumeSlider, GroupCard, ClientCard widgets
  - SourcesPanel, GroupsPanel, PropertiesPanel
  - Dark theme styling

- **CI/CD**
  - GitHub Actions with uv package manager
  - Claude Code Review integration
  - 230+ tests passing

### Fixed

- Encapsulation violations in GroupCard and SnapcastClient ([#1](https://github.com/lollonet/snapcast-mvp/pull/1))
- Server port: 1704 → 1705 (correct TCP control port)
