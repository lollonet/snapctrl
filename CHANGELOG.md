# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **SIGSEGV Crash in QWidget::ensurePolished()** ([#32](https://github.com/lollonet/snapctrl/pull/32)) - Feb 5
  - Replaced unsafe `QTimer.singleShot(0, ...)` from background thread with `_fallback_art_ready` Signal + explicit `QueuedConnection`
  - Added `deleteLater()` for removed GroupCard widgets to prevent dangling event pointers
  - Root cause: `QTimer.singleShot` from plain Python threads is undefined Qt behavior

- **Tray Menu Mute Button** ([#33](https://github.com/lollonet/snapctrl/pull/33)) - Feb 6
  - Connected `mute_toggled` signal so mute button in tray volume slider works
  - Added menu rebuild guard with `aboutToHide` handler to prevent erratic volume jumps

- **Volume Slider Snap-Back During Drag** ([#33](https://github.com/lollonet/snapctrl/pull/33)) - Feb 6
  - Added `isSliderDown()` guard to `set_volume()`, `set_muted()`, and `set_volume_and_mute()`
  - Server updates no longer snap slider position while user is dragging

- **Preferences Dialog Styling** ([#33](https://github.com/lollonet/snapctrl/pull/33)) - Feb 6
  - Restored dialog sizing (560×400) and input control styling (focus/read-only states)

### Changed

- **Magic Number Constants** ([#32](https://github.com/lollonet/snapctrl/pull/32)) - Feb 5
  - Wired `SNAPCLIENT_PORT`, `VOLUME_SLIDER_STALE_THRESHOLD`, `VOLUME_NOTIFICATION_DEBOUNCE_MS` constants
  - Extracted `_disconnect_process_signals()` helper in `snapclient_manager.py`

### Documentation

- **CLAUDE.md Added** ([#33](https://github.com/lollonet/snapctrl/pull/33)) - Feb 6
  - Project instructions for AI-assisted development (tech stack, conventions, quality gates)

- **README Test Count Updated** ([#33](https://github.com/lollonet/snapctrl/pull/33)) - Feb 6
  - Updated from 499 to 934 tests

### Maintenance

- **Test Lint Cleanup** ([#32](https://github.com/lollonet/snapctrl/pull/32)) - Feb 5
  - Fixed 160 ruff lint issues across 18 test files (PLC0415 imports, SIM117 nested `with`)
  - Added 8 new test files (934 total tests)

## [0.2.5] - 2026-02-05

### Fixed

- **External Snapclient Detach Crash** ([a7e68b0](https://github.com/lollonet/snapctrl/commit/a7e68b0)) - Feb 5
  - `detach()` crashed when snapclient was externally managed (no QProcess to detach)
  - Added guard to check process existence before detach

- **Album Art Aspect Ratio** ([9604942](https://github.com/lollonet/snapctrl/commit/9604942), [#31](https://github.com/lollonet/snapctrl/pull/31)) - Feb 5
  - Album art now preserves aspect ratio with `Qt.AspectRatioMode.KeepAspectRatio`
  - Tray menu rebuild performance optimized (debounced, fewer widget recreations)

## [0.2.4] - 2026-02-04

### Added

- **Auto-Connect Profile Priority** ([b24c545](https://github.com/lollonet/snapctrl/commit/b24c545)) - Feb 3
  - Saved server connections now take precedence over mDNS discovery on startup
  - Enables reliable connections to non-discoverable or remote servers

- **Preferences Dialog** (REQ-014) - Feb 2
  - Tabbed preferences dialog (Connection, Appearance, Local Client, Monitoring) accessible via status bar gear icon and system tray menu
  - Theme selection with live preview (Dark / Light / System)
  - Configurable ping interval, jitter poll interval, MPD host/port/poll interval
  - Local snapclient settings: enable toggle, binary path with file browser, auto-start, extra CLI args
  - All settings persisted via QSettings and applied immediately without restart
  - ConfigManager extended with theme, monitoring, and MPD settings accessors

- **QSpinBox Arrow Indicators** - Feb 2
  - CSS triangle arrows for QSpinBox up/down buttons (previously invisible on dark theme)
  - QComboBox hover border and dropdown arrow indicator

- **Connection-Aware Tray Icon** - Feb 2
  - Tray icon now shows green dot (connected) or red dot (disconnected) via QPainter overlay
  - Tooltip updates to "SnapCTRL — Connected" / "SnapCTRL — Disconnected"

- **Mute All / Unmute All** - Feb 2
  - System tray context menu now includes "Mute All" and "Unmute All" actions
  - Mutes/unmutes all groups on the server with a single click

- **UI Aesthetics Polish** - Feb 2
  - Platform-appropriate font stack: SF Pro (macOS), Segoe UI (Windows), Helvetica Neue (fallback)
  - Styled rename dialog replacing plain QInputDialog — themed background, accent OK button, focus ring
  - Global input control styling: QLineEdit, QSpinBox, QComboBox with themed borders, rounded corners, accent focus
  - Softer border radii (4→6px cards, 8→10px dialogs)

- **Resizable Album Art** - Feb 2
  - Cover art fills available panel width, scales dynamically on splitter drag/window resize
  - Changed from fixed 80×80px horizontal layout to vertical layout (art above text)
  - Qt `setScaledContents` with aspect-ratio-correct height for pixel-perfect rendering

### Changed

- **Typography Improvements** ([1c37847](https://github.com/lollonet/snapctrl/commit/1c37847)) - Feb 3
  - Increased font sizes in group cards, client cards, and properties panel for better readability (caption: 8→9pt, body: 10→11pt, title: 12→13pt)
  - Reduced vertical spacing in panel layouts for more compact display (spacing scale halved: xxs 2→1px, xs 4→2px, sm 8→4px)

### Fixed

- **Snapclient Process Detachment** ([d3ef070](https://github.com/lollonet/snapctrl/commit/d3ef070)) - Feb 3
  - Local snapclient process now properly detaches when user chooses "Don't Stop" on quit
  - Prevents orphaned process issues when closing the app while keeping local playback running

## [0.2.3] - 2026-02-02

### Added

- **Server-Side Jitter Stats** ([#24](https://github.com/lollonet/snapctrl/pull/24)) - Feb 2
  - Replaced ICMP ping to clients with server-measured jitter via `Client.GetTimeStats` JSON-RPC endpoint
  - Properties panel shows median jitter, P95 jitter, and sample count per client (requires snapserver fork with latency sampling)
  - Microsecond display for sub-millisecond values (e.g., "3µs" instead of "<1ms")
  - Graceful fallback when server doesn't support the endpoint or returns zero samples

- **Server Version in Status Bar** - Feb 2
  - Status bar now shows snapserver version alongside connection RTT (e.g., "Connected — v0.34.1 — 2.5ms")

### Fixed

- **GetTimeStats Key Names** - Feb 2
  - Corrected key names to match deployed server response (`jitter_median_ms`, `jitter_p95_ms` instead of `rtt_median_ms`, `rtt_p95_ms`)

- **HTML Escape in RTT Display** - Feb 2
  - `<1ms` values were invisible in properties panel because `<` was interpreted as HTML tag; now properly escaped

## [0.2.2] - 2026-02-01

### Fixed

- **CLI Argument Parsing** ([#21](https://github.com/lollonet/snapctrl/pull/21)) - Feb 1
  - Replaced manual `sys.argv` parsing with `argparse` — the old parser crashed with `ValueError` when using `--host`/`--port` flags (e.g., `open SnapCTRL.app --args --host raspy`)
  - Now supports both positional (`snapctrl raspy 1705`) and flag (`snapctrl --host raspy --port 1705`) syntax

- **macOS mDNS Server Discovery** ([#22](https://github.com/lollonet/snapctrl/pull/22)) - Feb 1
  - Added `NSLocalNetworkUsageDescription` and `NSBonjourServices` to macOS `Info.plist` — required since macOS 11 for mDNS/Bonjour access
  - Without these keys, the compiled `.app` bundle silently failed to discover Snapcast servers on the local network

## [0.2.1] - 2026-02-01

### Fixed

- **Group Mute Toggle** ([#20](https://github.com/lollonet/snapctrl/pull/20)) - Feb 1
  - The VolumeSlider's speaker icon (🔊/🔇) was not connected to the API — clicking it toggled mute visually but never sent `Group.SetMute` to the server
  - Removed the redundant dedicated "Mute" button; the slider's built-in speaker icon is now the single mute control per group

## [0.2.0] - 2026-01-30

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

- **Per-Client Latency Adjustment** ([#14](https://github.com/lollonet/snapctrl/pull/14)) - Jan 29
  - Interactive QSpinBox in Properties Panel (-1000 to +1000 ms, step 10)
  - `Client.SetLatency` API integration for audio sync fine-tuning
  - Shown only for connected clients; read-only display for disconnected

- **Design Tokens** ([#17](https://github.com/lollonet/snapctrl/pull/17)) - Jan 30
  - Frozen dataclass singletons for spacing (4px base unit), typography (pt scale), and sizing (border radii, icons, panel widths)
  - Replaced ~50 hardcoded magic numbers across 7 UI files with token references
  - Design system documentation (`docs/09-DESIGN-SYSTEM.md`)

- **Local Snapclient Manager** ([#19](https://github.com/lollonet/snapctrl/pull/19)) - Jan 30
  - QProcess-based subprocess lifecycle: start, stop, auto-restart on crash
  - Priority-ordered binary discovery (bundled → PATH → user-configured) with version validation
  - Exponential backoff restart (1s → 30s, max 5 attempts) with consecutive failure tracking
  - Stdout parsing for connection status and client ID detection (MAC/hostname regex)
  - Status bar indicator (running/starting/stopped/error with color coding)
  - System tray integration with start/stop toggle
  - Properties panel local client display
  - QSettings-based configuration (binary path, auto-start, extra args, server host)

### Changed

- **Package Rename** ([#16](https://github.com/lollonet/snapctrl/pull/16)) - Jan 29
  - Renamed source package `src/snapcast_mvp/` → `src/snapctrl/`
  - Updated ~250 references across imports, tests, configs, specs, and docs

### Maintenance

- **Claude Code GitHub Workflow** ([#18](https://github.com/lollonet/snapctrl/pull/18)) - Jan 30
  - GitHub Actions workflow for @claude mentions in PRs and issues

## [0.1.0] - 2026-01-29

### Added

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

- **Context Menus and Rename** ([#8](https://github.com/lollonet/snapctrl/pull/8)) - Jan 29
  - Right-click context menus on groups and clients
  - Inline rename for clients and groups via `Client.SetName` / `Group.SetName`

- **Connection Status Indicator** ([#7](https://github.com/lollonet/snapctrl/pull/7)) - Jan 29
  - Toolbar indicator with green/red dot and status text
  - Auto-reconnection with exponential backoff

- **Release Pipeline** ([#9](https://github.com/lollonet/snapctrl/pull/9)) - Jan 29
  - GitHub Actions builds for macOS, Windows, Linux on tag push
  - Automatic GitHub Release with platform binaries

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

- **Comprehensive Docs Audit** ([#15](https://github.com/lollonet/snapctrl/pull/15)) - Jan 29
  - Audited 28 docs against 40 source files, fixed 39 discrepancies
  - Added REQ-011 (Now Playing/MPD), REQ-012 (Advanced Client Controls), REQ-013 (Build & Release)
  - Fixed requirement statuses: REQ-009 Done, REQ-010 Partial, REQ-008 criteria rewritten
  - Rewrote architecture doc: module tree, StateStore signals, Worker pattern, threading model
  - Updated data models: Client fields, Group type fix, SourceStatus enum, MPD models
  - Added "Current Implementation" section to UI/UX doc
  - Fixed infrastructure: briefcase → PyInstaller, added zeroconf dependency
  - Updated README: features (5→15), test count (300+→400+), install command, roadmap
  - CI: added `.md` files to Claude review workflow filter

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
