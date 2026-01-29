"""Design tokens — single source of truth for spacing, sizing, typography.

Mirrors the pattern used by modern desktop apps (Spotify, VS Code, Discord).
Color tokens live in theme.py (ThemePalette). Layout tokens live here.

Usage:
    from snapctrl.ui.tokens import spacing, typography, sizing

    layout.setContentsMargins(spacing.sm, spacing.sm, spacing.sm, spacing.sm)
    header.setStyleSheet(f"font-size: {typography.title}pt;")
    widget.setFixedSize(sizing.icon_md, sizing.icon_md)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpacingTokens:
    """Spacing scale based on a 4px base unit."""

    xxs: int = 2  # Tight: inner padding
    xs: int = 4  # Default: margins, small gaps
    sm: int = 8  # Comfortable: card padding, between elements
    md: int = 12  # Loose: between cards, section gaps
    lg: int = 16  # Spacious: panel padding
    xl: int = 24  # Layout: between major sections


@dataclass(frozen=True)
class TypographyTokens:
    """Font size scale in points."""

    caption: int = 8  # IDs, fine print
    small: int = 9  # Status text, badges
    body: int = 10  # Default body text
    subtitle: int = 11  # Toolbar, secondary headers
    title: int = 12  # Panel headers
    heading: int = 14  # Dialog titles


@dataclass(frozen=True)
class SizingTokens:
    """Widget sizing constants in pixels."""

    border_radius_sm: int = 2  # Badges, small elements
    border_radius_md: int = 4  # Cards, buttons
    border_radius_lg: int = 8  # Dialogs, panels
    icon_sm: int = 16  # Inline icons
    icon_md: int = 24  # Toolbar icons
    icon_lg: int = 32  # Panel header icons
    album_art: int = 80  # Album art thumbnail
    control_button: int = 32  # Transport control buttons
    panel_min_side: int = 150  # Min side panel width
    panel_max_side: int = 300  # Max side panel width


# Module-level singletons — import these in widgets
spacing = SpacingTokens()
typography = TypographyTokens()
sizing = SizingTokens()
