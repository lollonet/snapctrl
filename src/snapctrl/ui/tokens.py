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

    xxs: int = 1  # Tight: inner padding
    xs: int = 2  # Default: margins, small gaps
    sm: int = 4  # Comfortable: card padding, between elements
    md: int = 8  # Loose: between cards, section gaps
    lg: int = 12  # Spacious: panel padding
    xl: int = 16  # Layout: between major sections


@dataclass(frozen=True)
class TypographyTokens:
    """Font size scale in points and font family stack."""

    font_family: str = "'SF Pro Text', 'Segoe UI', 'Helvetica Neue', sans-serif"
    caption: int = 9  # IDs, fine print
    small: int = 10  # Status text, badges
    body: int = 11  # Default body text
    subtitle: int = 12  # Toolbar, secondary headers
    title: int = 13  # Panel headers
    heading: int = 15  # Dialog titles


@dataclass(frozen=True)
class SizingTokens:
    """Widget sizing constants in pixels."""

    border_radius_sm: int = 2  # Badges, small elements
    border_radius_md: int = 6  # Cards, buttons
    border_radius_lg: int = 10  # Dialogs, panels
    icon_sm: int = 16  # Inline icons
    icon_md: int = 24  # Toolbar icons
    icon_lg: int = 32  # Panel header icons
    emoji_indicator: int = 14  # Status indicator emoji (px)
    emoji_button: int = 16  # Button emoji / icon font (px)
    album_art: int = 80  # Album art thumbnail
    control_button: int = 32  # Transport control buttons
    scrollbar_width: int = 8  # Scrollbar track width/height
    scrollbar_min_handle: int = 20  # Min scrollbar handle dimension
    panel_min_side: int = 150  # Min side panel width
    panel_max_side: int = 300  # Max side panel width


# Module-level singletons — import these in widgets
spacing = SpacingTokens()
typography = TypographyTokens()
sizing = SizingTokens()
