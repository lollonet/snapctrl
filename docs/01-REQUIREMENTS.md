# SnapCTRL - Requirements

## Functional Requirements

### REQ-001: Server Connection
The app MUST connect to a Snapcast server via TCP on port 1705 (default control port).

**Acceptance Criteria:**
- [ ] Connect using IP address or hostname
- [ ] Discover servers on local network via mDNS
- [ ] Save multiple connection profiles
- [ ] Auto-connect to last used server on startup
- [ ] Show connection status (connected/disconnected/connecting)

**Priority:** P0 (MVP)
**Domain:** Connection
**Source:** VISION § Problem Statement

---

### REQ-002: Server State Display
The app MUST display the current state of the Snapcast server.

**Acceptance Criteria:**
- [ ] List all audio groups with member clients
- [ ] Show each client's name, host, and online status
- [ ] Display available audio sources
- [ ] Show which source each group is playing
- [ ] Update in real-time via TCP notifications

**Priority:** P0 (MVP)
**Domain:** Display
**Source:** VISION § Success Metrics

---

### REQ-003: Group Volume Control
The app MUST provide volume control for each group.

**Acceptance Criteria:**
- [ ] Volume slider (0-100%) per group
- [ ] Mute/unmute toggle per group
- [ ] Visual feedback when volume changes
- [ ] Volume changes apply to all clients in group
- [ ] Show current volume percentage

**Priority:** P0 (MVP)
**Domain:** Control
**Source:** User Interview Q5

---

### REQ-004: Client Volume Control
The app MUST provide individual volume control for each client.

**Acceptance Criteria:**
- [ ] Volume slider (0-100%) per client
- [ ] Mute/unmute toggle per client
- [ ] Client volume independent of group volume
- [ ] Expandable within group card to show client controls

**Priority:** P1 (Important)
**Domain:** Control
**Source:** User Interview Q5

---

### REQ-005: Source Switching
The app MUST allow changing the audio source for any group.

**Acceptance Criteria:**
- [ ] Dropdown selector of available sources per group
- [ ] Show current source for each group
- [ ] Visual indicator when source is playing
- [ ] Instant source change on selection

**Priority:** P0 (MVP)
**Domain:** Control
**Source:** User Interview Q6

---

### REQ-006: Client Details View
The app MUST display detailed information for each client.

**Acceptance Criteria:**
- [ ] Client name (editable)
- [ ] Host IP/hostname
- [ ] MAC address
- [ ] Connection status (online/offline)
- [ ] Current volume and mute state
- [x] Latency value (interactive for connected clients, read-only for disconnected)
- [ ] Snapclient version

**Priority:** P1 (Important)
**Domain:** Display
**Source:** User Interview Q8

---

### REQ-007: Connection Profiles
The app MUST support multiple server connection profiles.

**Acceptance Criteria:**
- [ ] Add/edit/delete server profiles
- [ ] Store: name, host, port
- [ ] Quick switch between saved profiles
- [ ] Profiles persist across app restarts

**Priority:** P1 (Important)
**Domain:** Connection
**Source:** User Interview Q4

---

### REQ-008: Auto-Reconnection
The app MUST automatically attempt to reconnect when connection is lost.

**Acceptance Criteria:**
- [x] Detect connection loss via TCP read failure
- [x] Attempt reconnection with exponential backoff (2s initial, 30s max)
- [x] Show connection status in toolbar indicator (green/red dot + text)
- [x] Retry indefinitely until connection restored
- [x] Resume full state refresh on reconnection

**Priority:** P1 (Important)
**Domain:** Connection
**Source:** VISION § Non-Negotiables

---

### REQ-009: System Theme Support
The app MUST follow the system theme (light/dark mode).

**Acceptance Criteria:**
- [x] Detect system theme at startup
- [x] Switch theme when system theme changes (runtime, macOS dark mode toggle)
- [x] Light theme with good contrast (22-color ThemePalette)
- [x] Dark theme with good contrast (22-color ThemePalette)

**Priority:** P1 (Important)
**Domain:** UI/UX
**Source:** User Interview Q9

---

### REQ-010: System Tray Integration
The app MUST provide a system tray icon.

**Acceptance Criteria:**
- [x] Minimize to tray instead of closing (close-to-tray behavior)
- [ ] Tray icon shows connection status (currently static icon)
- [x] Right-click menu: Show/Hide, Quit
- [x] Quick volume controls for each group (embedded QWidgetAction slider)
- [ ] Mute All / Unmute All

**Priority:** P1 (Important)
**Domain:** UI/UX
**Source:** User Interview Q10

---

## Non-Functional Requirements

### NFR-001: Performance
| Metric | Target |
|--------|--------|
| Startup time | < 2 seconds |
| Volume change latency | < 100ms |
| Memory usage | < 200MB |
| TCP message handling | < 50ms |

### NFR-002: Platform Support
- Windows 10/11 (MSIX installer)
- macOS 12+ (DMG, signed)
- Linux (AppImage, Flatpak)

### NFR-003: Quality
- Linter: Ruff (strict mode)
- Type checker: basedpyright (strict mode)
- Test coverage: ≥ 70%
- Pre-commit hooks required

### NFR-004: Accessibility
- Full keyboard navigation
- Screen reader support (platform APIs)
- Minimum contrast ratio 4.5:1 (WCAG AA)

---

## Requirements Summary

| ID | Title | Priority | Domain | Status |
|----|-------|----------|--------|--------|
| REQ-001 | Server Connection | P0 | Connection | Done |
| REQ-002 | Server State Display | P0 | Display | Done |
| REQ-003 | Group Volume Control | P0 | Control | Done |
| REQ-004 | Client Volume Control | P1 | Control | Done |
| REQ-005 | Source Switching | P0 | Control | Done |
| REQ-006 | Client Details View | P1 | Display | Done |
| REQ-007 | Connection Profiles | P1 | Connection | Draft |
| REQ-008 | Auto-Reconnection | P1 | Connection | Done |
| REQ-009 | System Theme Support | P1 | UI/UX | Done |
| REQ-010 | System Tray Integration | P1 | UI/UX | Partial |
| REQ-011 | Now Playing & MPD Integration | P1 | Display | Done |
| REQ-012 | Advanced Client Controls | P1 | Control | Done |
| REQ-013 | Build & Release Pipeline | P1 | Infrastructure | Done |

---

*Next: [Architecture](docs/02-ARCHITECTURE.md) →*
