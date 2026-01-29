# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **System Tray Icon** ([#13](https://github.com/lollonet/snapctrl/pull/13)) - Jan 29
  - Show/Hide window toggle (double-click or menu)
  - Group status entries with average volume percentages
  - Now Playing metadata from sources
  - Quick volume slider embedded in tray menu (QWidgetAction)
  - Quit action; close-to-tray behavior (hide instead of quit)
  - Debounced menu rebuild on state changes (500ms)

- **Centralized Theme System** ([#13](https://github.com/lollonet/snapctrl/pull/13)) - Jan 29
  - ThemeManager singleton with dark/light palette auto-detection (Qt 6.5+ colorScheme API)
  - ThemePalette dataclass with 22 named color fields
  - Runtime theme switching on macOS dark mode toggle
  - Replaced ~40 hardcoded hex setStyleSheet calls across 7 UI files with palette lookups

- **Mute-Only API** ([#2](https://github.com/lollonet/snapctrl/pull/2)) - Jan 27
  - `set_client_mute()` method for mute operations without volume data
  - Prevents duplicate API calls when toggling mute
  - CLI entry point with host/port argument parsing

- **mDNS Autodiscovery** ([#3](https://github.com/lollonet/snapctrl/pull/3)) - Jan 27
  - Automatic Snapcast server discovery on local network
  - Zero-configuration startup when no arguments provided
  - Shows FQDN and IP in window title (e.g., "raspy.local (192.168.63.3)")

- **Source Details Panel** ([#5](https://github.com/lollonet/snapctrl/pull/5)) - Jan 27
  - Status indicator (Playing/Idle) with color coding
  - Stream type, codec, and sample format display
  - Human-readable format (e.g., "48kHz/16bit/stereo")

- **Enhanced Client Properties** ([#5](https://github.com/lollonet/snapctrl/pull/5)) - Jan 27
  - System info (OS and architecture)
  - Last seen timestamp with human-readable format
  - Network RTT ping measurement (updated every 15 seconds)
  - Color-coded latency: green (<50ms), yellow (50-100ms), red (>100ms)

- **Cross-Platform Build Configuration** - Jan 27
  - PyInstaller spec files for macOS, Windows, and Linux
  - Automated build script (`scripts/build.py`)
  - Windows .ico icon (multi-resolution)
  - macOS .app bundle with .dmg packaging

- **App Rebranding** - Jan 27
  - Project renamed to "SnapCTRL"
  - Custom app icon (SVG, ICNS, ICO)
  - macOS app bundle with proper Info.plist

- **Now Playing Metadata** - Jan 28
  - Display track title, artist, and album for playing sources
  - Album art display (80x80px with rounded corners)
  - Metadata from Snapcast server streams

- **MPD Protocol Integration** - Jan 28
  - Full MPD client with async TCP connection
  - Track metadata (title, artist, album) via `currentsong`
  - Album art via `readpicture` and `albumart` commands
  - MpdMonitor for real-time track change detection (2s polling)

- **Album Art Fallback Chain** - Jan 28
  - iTunes Search API for broad coverage
  - MusicBrainz Cover Art Archive as fallback
  - Triggers on source selection and track change
  - Handles Snapcast HTTP server bugs gracefully

### Fixed

- **Source Selection** ([#4](https://github.com/lollonet/snapctrl/pull/4)) - Jan 27
  - Dropdown now correctly changes stream on server
  - Fixed API parameter naming (`stream_id` instead of `streamId`)

- **Group Volume Sync** ([#4](https://github.com/lollonet/snapctrl/pull/4)) - Jan 27
  - Slider shows actual average volume (not fixed 50%)
  - Client sliders follow group slider visually
  - Syncs with external changes (mobile app) after 1s inactivity
  - Auto-mute when volume reaches 0

- **Signal Handling** ([#2](https://github.com/lollonet/snapctrl/pull/2)) - Jan 27
  - Fixed VolumeSlider signal cascading on mute toggle
  - Blocks signals during programmatic updates

- **Connection Status** ([#4](https://github.com/lollonet/snapctrl/pull/4)) - Jan 27
  - Green/red color indicators for connected/disconnected
  - Properties panel updates when client selected

- **Album Art Chunked Retrieval** - Jan 28
  - MPD returns album art in 8KB chunks
  - Now fetches all chunks for complete images

- **HTTP Album Art URLs** - Jan 28
  - Support for Snapcast image cache URLs
  - URL hostname rewriting (internal hostname → connection IP)

- **MPD Album Art Race Conditions** ([#6](https://github.com/lollonet/snapctrl/pull/6)) - Jan 28
  - Generation counter to cancel stale fallback requests
  - `_art_loaded` flag prevents fallback overwriting valid art
  - Metadata preservation when Snapcast sends empty updates

### Documentation

- **Project Rename** - Jan 28
  - All docs updated from "Snapcast MVP" to "SnapCTRL"
  - Fixed critical error: "WebSocket port 1704" → "TCP port 1705"
  - Updated requirement statuses (7 Done, 3 Draft)
  - Created missing ADR directory
  - Fixed architecture and technology index structure

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
  - 360+ tests passing

### Fixed

- Encapsulation violations in GroupCard and SnapcastClient ([#1](https://github.com/lollonet/snapctrl/pull/1))
- Server port: 1704 → 1705 (correct TCP control port)
