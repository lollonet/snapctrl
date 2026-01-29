# SnapCTRL - UI/UX Design

## Current Implementation

The application uses a tri-pane layout with a toolbar (no menu bar). Key differences from the original mockup below:

- **No menu bar** — toolbar with connection status indicator (green/red dot + text)
- **Sources panel** — read-only list from server (no "+ Add Source" button)
- **Groups panel** — scrollable group cards with source dropdown, context menus for rename
- **Properties panel** — interactive latency spinbox for connected clients, context menu rename
- **System tray** — minimize-to-tray, quick volume sliders, now playing metadata
- **Theme** — auto dark/light mode detection, runtime switching (macOS)
- **No responsive breakpoints** — fixed tri-pane layout

### Panel Specifications (Actual)

| Panel | Width | Content | Interactions |
|-------|-------|---------|--------------|
| **Sources** (left) | 150-250px | List of audio sources with playing indicator, now playing metadata | Click to view details |
| **Groups** (center) | flexible | Group cards with volume slider, mute, source dropdown | Drag slider, click mute, select source, right-click context menu |
| **Properties** (right) | 200-300px | Details of selected item, interactive latency control | Latency spinbox (connected clients), read-only info |

---

## Original Design Mockup

> **Note:** This wireframe was the initial design. See "Current Implementation" above for what was actually built. Elements marked (Planned) are not yet implemented.

## Layout: Tri-Pane Dashboard

```
┌──────────────────────────────────────────────────────────────────────┐
│ Menu Bar (File, Edit, View, Help)                                   │
├──────────────────────────────────────────────────────────────────────┤
│ ┌──────────────┬─────────────────────────────────┬─────────────────┐│
│ │              │                                 │                 ││
│ │  SOURCES     │         GROUPS & CLIENTS        │   PROPERTIES    ││
│ │              │                                 │                 ││
│ │ 🎵 Spotify   │  ┌───────────────────────────┐ │  Selected:      ││
│ │   ▶ Playing  │  │ Living Room    [🔊][≡]    │ │  Living Room    ││
│ │              │  │ 🎵 Spotify                │ │                 ││
│ │ 📻 Radio     │  │ ━━━━━━━━━━◉───── 75% [🔇] │ │  Volume: 75%    ││
│ │   ○ Idle     │  │                          │ │  Muted: No      ││
│ │              │  │ ▸ Clients (2)             │ │  Source:        ││
│ │ 🎸 Line-in   │  │   ● TV Speaker (65%)     │ │  Spotify        ││
───────────────────  │   ● Bookshelf (85%)      │ │                 ││
│              │  └───────────────────────────┘ │  Clients: 2/2   ││
│ + Add Source │  ┌───────────────────────────┐ │  Online: Yes     ││
│              │  │ Kitchen       [🔊][≡]       │ │                 ││
│              │  │ 🎵 Spotify                │ │  [Edit Group]   ││
│              │  │ ━━━━━━━━━━━◉───── 85% [🔇]│ │                 ││
│              │  │                          │ │                 ││
│              │  │ ▸ Clients (1)             │ │                 ││
│              │  │   ● Smart Speaker (85%)   │ │                 ││
│              │  └───────────────────────────┘ │                 ││
│              │                                 │                 ││
│              │  [+ New Group]                  │                 ││
│              │                                 │                 ││
└───────────────────────┴─────────────────────────────────┴─────────────────┘
│ Status: Connected to Home server • 3 clients online • Last sync: 1s ago    │
└──────────────────────────────────────────────────────────────────────────────┘
```

## Panel Specifications

| Panel | Width | Content | Interactions |
|-------|-------|---------|--------------|
| **Sources** (left) | 240px | List of audio sources with playing indicator | Click to view details |
| **Groups** (center) | flexible | Group cards with volume slider, mute, source selector | Drag slider, click mute, select source |
| **Properties** (right) | 280px | Details of selected item | Read-only (editable in future) |

## Visual States

| State | Color | Icon |
|-------|-------|------|
| Connected | Green (#4CAF50) | ● |
| Connecting | Yellow (#FFA500) | ⟳ |
| Disconnected | Red (#f44336) | ● |
| Playing | Green (#4CAF50) | ▶ |
| Idle | Gray (#999) | ○ |

## Responsive Behavior (Planned/Future)

> **Note:** Not yet implemented. The current layout is a fixed tri-pane.

| Window Width | Behavior |
|--------------|----------|
| < 1024px | Collapse sources panel to overlay |
| < 768px | Stack panels vertically (mobile-ish) |
| 1024-1600px | Standard tri-pane |
| > 1600px | Wider panels, 2-column group grid |

---

*Next: [Security](docs/05-SECURITY.md) →*
