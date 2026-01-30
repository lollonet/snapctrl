"""Centralized theme system with dark/light mode detection.

Provides a ThemeManager singleton that detects the system color scheme,
exposes named color palettes, and emits signals on theme changes.

Usage:
    from snapctrl.ui.theme import theme_manager

    palette = theme_manager.palette
    widget.setStyleSheet(f"background-color: {palette.background};")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import cast

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication

from snapctrl.ui.tokens import sizing, spacing

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThemePalette:
    """Named color palette for UI theming.

    All values are CSS color strings (e.g. '#1e1e1e' or 'rgba(...)').
    """

    # Backgrounds
    background: str  # App/window background
    surface: str  # Widget/card background
    surface_hover: str  # Widget hover state
    surface_selected: str  # Widget selected state
    surface_dim: str  # Subdued surface (e.g. client card)

    # Borders
    border: str  # Default border
    border_selected: str  # Selected item border

    # Text
    text: str  # Primary text
    text_secondary: str  # Secondary/muted text
    text_disabled: str  # Disabled text

    # Status colors
    success: str  # Connected / good
    error: str  # Disconnected / error
    warning: str  # Warning state
    accent: str  # Brand accent (orange)

    # Semantic
    scrollbar: str  # Scrollbar thumb
    scrollbar_hover: str  # Scrollbar thumb hover

    # Elevated surfaces (cards on panels)
    surface_elevated: str  # Card background sitting on surface
    surface_success: str  # Green-tinted surface (connected status)
    surface_error: str  # Red-tinted surface (disconnected / mute active)

    # Volume slider
    slider_groove: str  # Slider track
    slider_fill: str  # Slider filled portion
    slider_handle: str  # Slider thumb

    @property
    def name(self) -> str:
        """Return 'dark' or 'light' based on background luminance."""
        # Simple heuristic: dark backgrounds have low hex values
        _luminance_threshold = 128
        if self.background.startswith("#"):
            r = int(self.background[1:3], 16)
            return "dark" if r < _luminance_threshold else "light"
        return "dark"


DARK_PALETTE = ThemePalette(
    background="#1e1e1e",
    surface="#2d2d2d",
    surface_hover="#404040",
    surface_selected="#3a3a5a",
    surface_dim="#2a2a2a",
    border="#333333",
    border_selected="#6a6a9a",
    text="#e0e0e0",
    text_secondary="#aaaaaa",
    text_disabled="#666666",
    success="#4CAF50",
    error="#F44336",
    warning="#ffff80",
    accent="#FF8C00",
    scrollbar="#555555",
    scrollbar_hover="#777777",
    surface_elevated="#353535",
    surface_success="#2d5a2d",
    surface_error="#5a2d2d",
    slider_groove="#444444",
    slider_fill="#4CAF50",
    slider_handle="#cccccc",
)

LIGHT_PALETTE = ThemePalette(
    background="#f5f5f5",
    surface="#ffffff",
    surface_hover="#e8e8e8",
    surface_selected="#d0d0f0",
    surface_dim="#eeeeee",
    border="#cccccc",
    border_selected="#8080c0",
    text="#1a1a1a",
    text_secondary="#555555",
    text_disabled="#999999",
    success="#388E3C",
    error="#D32F2F",
    warning="#F9A825",
    accent="#E67E00",
    scrollbar="#bbbbbb",
    scrollbar_hover="#999999",
    surface_elevated="#f0f0f0",
    surface_success="#c8e6c9",
    surface_error="#ffcdd2",
    slider_groove="#cccccc",
    slider_fill="#388E3C",
    slider_handle="#555555",
)


class ThemeManager(QObject):
    """Manages the application theme and reacts to system changes.

    Detects the system color scheme (dark/light) and provides a ThemePalette.
    Emits ``theme_changed`` when the palette switches.

    Example:
        theme_manager.apply_theme()
        theme_manager.theme_changed.connect(my_widget.refresh_style)
    """

    theme_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._palette = DARK_PALETTE

    @property
    def palette(self) -> ThemePalette:
        """Return the current color palette."""
        return self._palette

    @property
    def is_dark(self) -> bool:
        """Return True if the current theme is dark."""
        return self._palette.name == "dark"

    def detect_system_theme(self) -> ThemePalette:
        """Detect the system color scheme and return the matching palette.

        Uses Qt 6.5+ ``QStyleHints.colorScheme()`` API.
        Falls back to dark theme if detection fails.
        """
        try:
            raw_app = QGuiApplication.instance()
            if raw_app is None:
                return DARK_PALETTE
            app = cast(QGuiApplication, raw_app)
            hints = app.styleHints()
            # Qt.ColorScheme.Dark == 2, Light == 1 (Qt 6.5+)
            from PySide6.QtCore import Qt  # noqa: PLC0415

            scheme = hints.colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return LIGHT_PALETTE
            return DARK_PALETTE
        except AttributeError:
            # Qt < 6.5 or no colorScheme support
            logger.debug("System theme detection not available, using dark theme")
            return DARK_PALETTE

    def apply_theme(self, palette: ThemePalette | None = None) -> None:
        """Apply a theme palette to the application.

        Args:
            palette: Palette to apply. If None, auto-detects from system.
        """
        if palette is None:
            palette = self.detect_system_theme()

        old_name = self._palette.name
        self._palette = palette
        logger.info("Theme applied: %s", palette.name)

        # Set global stylesheet on QApplication for scrollbars etc.
        raw_app = QApplication.instance()
        if raw_app is not None:
            qapp = cast(QApplication, raw_app)
            qapp.setStyleSheet(self._global_stylesheet())

        if palette.name != old_name:
            self.theme_changed.emit()

    def connect_system_theme_changes(self) -> None:
        """Listen for runtime system theme changes (e.g. macOS dark mode toggle)."""
        try:
            raw_app = QGuiApplication.instance()
            if raw_app is None:
                return
            app = cast(QGuiApplication, raw_app)
            hints = app.styleHints()
            hints.colorSchemeChanged.connect(self._on_system_theme_changed)
            logger.debug("Connected to system theme change signal")
        except AttributeError:
            logger.debug("System theme change signal not available")

    def _on_system_theme_changed(self) -> None:
        """Handle runtime system theme change."""
        logger.info("System theme changed, re-applying")
        self.apply_theme()

    def _global_stylesheet(self) -> str:
        """Generate a global stylesheet for QApplication."""
        p = self._palette
        return f"""
            QToolTip {{
                background-color: {p.surface};
                color: {p.text};
                border: 1px solid {p.border};
                padding: {spacing.xs}px;
            }}
            QScrollBar:vertical {{
                background: {p.background};
                width: {sizing.scrollbar_width}px;
            }}
            QScrollBar::handle:vertical {{
                background: {p.scrollbar};
                min-height: {sizing.scrollbar_min_handle}px;
                border-radius: {sizing.border_radius_md}px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {p.scrollbar_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar:horizontal {{
                background: {p.background};
                height: {sizing.scrollbar_width}px;
            }}
            QScrollBar::handle:horizontal {{
                background: {p.scrollbar};
                min-width: {sizing.scrollbar_min_handle}px;
                border-radius: {sizing.border_radius_md}px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {p.scrollbar_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
        """


# Module-level singleton — import this in widgets
theme_manager = ThemeManager()
