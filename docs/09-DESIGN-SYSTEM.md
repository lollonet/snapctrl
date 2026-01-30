# 09 — Design System

> Single source of truth for SnapCTRL's visual language.

## Overview

SnapCTRL uses a **Design Tokens + Atomic Design** approach — the same pattern adopted by Spotify, Discord, VS Code, and other modern desktop applications.

- **Color tokens** → `src/snapctrl/ui/theme.py` (ThemePalette, 22 named fields)
- **Layout tokens** → `src/snapctrl/ui/tokens.py` (spacing, typography, sizing)

All UI files import from these two modules. No magic numbers in widget code.

---

## Design Tokens

### Spacing Scale (4px base unit)

| Token | Value | Usage |
|-------|-------|-------|
| `spacing.xxs` | 2px | Tight: inner padding |
| `spacing.xs` | 4px | Default: margins, small gaps |
| `spacing.sm` | 8px | Comfortable: card padding, between elements |
| `spacing.md` | 12px | Loose: between cards, section gaps |
| `spacing.lg` | 16px | Spacious: panel padding |
| `spacing.xl` | 24px | Layout: between major sections |

### Typography Scale (pt)

| Token | Value | Usage |
|-------|-------|-------|
| `typography.caption` | 8pt | IDs, fine print |
| `typography.small` | 9pt | Status text, badges |
| `typography.body` | 10pt | Default body text |
| `typography.subtitle` | 11pt | Toolbar, secondary headers |
| `typography.title` | 12pt | Panel headers |
| `typography.heading` | 14pt | Dialog titles |

### Sizing Constants (px)

| Token | Value | Usage |
|-------|-------|-------|
| `sizing.border_radius_sm` | 2px | Badges, small elements |
| `sizing.border_radius_md` | 4px | Cards, buttons |
| `sizing.border_radius_lg` | 8px | Dialogs, panels |
| `sizing.icon_sm` | 16px | Inline icons |
| `sizing.icon_md` | 24px | Toolbar icons |
| `sizing.icon_lg` | 32px | Panel header icons |
| `sizing.emoji_indicator` | 14px | Status indicator emoji |
| `sizing.emoji_button` | 16px | Button emoji / icon font |
| `sizing.album_art` | 80px | Album art thumbnail |
| `sizing.control_button` | 32px | Transport control buttons |
| `sizing.scrollbar_width` | 8px | Scrollbar track width/height |
| `sizing.scrollbar_min_handle` | 20px | Min scrollbar handle dimension |
| `sizing.panel_min_side` | 150px | Min side panel width |
| `sizing.panel_max_side` | 300px | Max side panel width |

### Color Tokens (ThemePalette)

See `src/snapctrl/ui/theme.py` — 22 named color fields with automatic dark/light detection via Qt 6.5+ `colorScheme` API. Examples:

- `p.background`, `p.surface`, `p.surface_dim`, `p.surface_elevated`
- `p.text`, `p.text_secondary`, `p.text_disabled`
- `p.success`, `p.error`, `p.warning`
- `p.border`, `p.border_selected`

---

## Component Hierarchy (Atomic Design)

```
ATOMS (base elements):
  ThemePalette          ← theme.py (colors)
  SpacingTokens         ← tokens.py (layout spacing)
  TypographyTokens      ← tokens.py (font sizes)
  SizingTokens          ← tokens.py (dimensions)

MOLECULES (simple widgets):
  VolumeSlider          ← widgets/volume_slider.py

ORGANISMS (composite widgets):
  GroupCard             ← widgets/group_card.py
  ClientCard            ← widgets/client_card.py

TEMPLATES (panels):
  SourcesPanel          ← panels/sources.py
  GroupsPanel           ← panels/groups.py
  PropertiesPanel       ← panels/properties.py

PAGE:
  MainWindow            ← main_window.py (tri-pane layout)
  SystemTrayManager     ← system_tray.py
```

---

## Usage Patterns

### Import tokens

```python
from snapctrl.ui.tokens import spacing, typography, sizing
from snapctrl.ui.theme import theme_manager
```

### Layout margins and spacing

```python
layout.setContentsMargins(spacing.sm, spacing.sm, spacing.sm, spacing.sm)
layout.setSpacing(spacing.xs)
```

### Stylesheets with tokens

```python
p = theme_manager.palette
widget.setStyleSheet(f"""
    QWidget {{
        background-color: {p.surface};
        border-radius: {sizing.border_radius_md}px;
        padding: {spacing.xs}px {spacing.sm}px;
        font-size: {typography.body}pt;
        color: {p.text};
    }}
""")
```

### Fixed widget sizes

```python
button.setFixedSize(sizing.control_button, sizing.control_button)
icon.setFixedSize(sizing.icon_md, sizing.icon_md)
art.setFixedSize(sizing.album_art, sizing.album_art)
```

---

## Rules

1. **No magic numbers in UI code.** All spacing, sizing, font-size, and border-radius values must come from tokens.
2. **No hardcoded colors.** Use `theme_manager.palette` fields.
3. **Tokens are frozen dataclasses.** Immutable at runtime — values are set at import time.
4. **Module-level singletons.** Use `spacing`, `typography`, `sizing` — not `SpacingTokens()`.
5. **Extend tokens, don't override.** If a new size is needed, add a field to the dataclass.
