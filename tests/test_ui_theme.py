"""Tests for the centralized theme system."""

from unittest.mock import MagicMock, patch

from PySide6.QtCore import Qt

from snapctrl.ui.theme import (
    DARK_PALETTE,
    LIGHT_PALETTE,
    ThemeManager,
    ThemePalette,
)


class TestThemePalette:
    """Test ThemePalette dataclass."""

    def test_dark_palette_name(self) -> None:
        """Test that dark palette reports 'dark'."""
        assert DARK_PALETTE.name == "dark"

    def test_light_palette_name(self) -> None:
        """Test that light palette reports 'light'."""
        assert LIGHT_PALETTE.name == "light"

    def test_palette_is_frozen(self) -> None:
        """Test that palette is immutable."""
        try:
            DARK_PALETTE.background = "#000000"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass

    def test_dark_palette_has_all_fields(self) -> None:
        """Test that dark palette has all expected color fields."""
        assert DARK_PALETTE.background
        assert DARK_PALETTE.surface
        assert DARK_PALETTE.surface_hover
        assert DARK_PALETTE.surface_selected
        assert DARK_PALETTE.surface_dim
        assert DARK_PALETTE.surface_elevated
        assert DARK_PALETTE.surface_success
        assert DARK_PALETTE.surface_error
        assert DARK_PALETTE.border
        assert DARK_PALETTE.border_selected
        assert DARK_PALETTE.text
        assert DARK_PALETTE.text_secondary
        assert DARK_PALETTE.text_disabled
        assert DARK_PALETTE.success
        assert DARK_PALETTE.error
        assert DARK_PALETTE.warning
        assert DARK_PALETTE.accent
        assert DARK_PALETTE.scrollbar
        assert DARK_PALETTE.scrollbar_hover
        assert DARK_PALETTE.slider_groove
        assert DARK_PALETTE.slider_fill
        assert DARK_PALETTE.slider_handle

    def test_light_palette_has_all_fields(self) -> None:
        """Test that light palette has all expected color fields."""
        assert LIGHT_PALETTE.background
        assert LIGHT_PALETTE.surface
        assert LIGHT_PALETTE.text

    def test_palette_name_heuristic_dark(self) -> None:
        """Test name heuristic for a dark background."""
        palette = ThemePalette(
            background="#1e1e1e",
            surface="",
            surface_hover="",
            surface_selected="",
            surface_dim="",
            surface_elevated="",
            surface_success="",
            surface_error="",
            border="",
            border_selected="",
            text="",
            text_secondary="",
            text_disabled="",
            success="",
            error="",
            warning="",
            accent="",
            accent_hover="",
            scrollbar="",
            scrollbar_hover="",
            slider_groove="",
            slider_fill="",
            slider_handle="",
        )
        assert palette.name == "dark"

    def test_palette_name_heuristic_light(self) -> None:
        """Test name heuristic for a light background."""
        palette = ThemePalette(
            background="#f5f5f5",
            surface="",
            surface_hover="",
            surface_selected="",
            surface_dim="",
            surface_elevated="",
            surface_success="",
            surface_error="",
            border="",
            border_selected="",
            text="",
            text_secondary="",
            text_disabled="",
            success="",
            error="",
            warning="",
            accent="",
            accent_hover="",
            scrollbar="",
            scrollbar_hover="",
            slider_groove="",
            slider_fill="",
            slider_handle="",
        )
        assert palette.name == "light"


class TestThemeManager:
    """Test ThemeManager."""

    def test_default_palette_is_dark(self) -> None:
        """Test that default palette is dark."""
        manager = ThemeManager()
        assert manager.palette.name == "dark"
        assert manager.is_dark

    def test_apply_dark_theme(self) -> None:
        """Test applying dark theme."""
        manager = ThemeManager()
        manager.apply_theme(DARK_PALETTE)
        assert manager.palette is DARK_PALETTE
        assert manager.is_dark

    def test_apply_light_theme(self) -> None:
        """Test applying light theme."""
        manager = ThemeManager()
        manager.apply_theme(LIGHT_PALETTE)
        assert manager.palette is LIGHT_PALETTE
        assert not manager.is_dark

    def test_theme_changed_signal(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test that theme_changed signal emits on palette switch."""
        manager = ThemeManager()
        signals_received: list[bool] = []
        manager.theme_changed.connect(lambda: signals_received.append(True))

        # Switch from dark (default) to light
        manager.apply_theme(LIGHT_PALETTE)
        assert len(signals_received) == 1

    def test_theme_changed_not_emitted_for_same_theme(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test that signal is NOT emitted when applying same theme."""
        manager = ThemeManager()
        signals_received: list[bool] = []
        manager.theme_changed.connect(lambda: signals_received.append(True))

        # Apply dark again (already dark by default)
        manager.apply_theme(DARK_PALETTE)
        assert len(signals_received) == 0

    def test_detect_system_theme_without_app(self) -> None:
        """Test that detect_system_theme falls back to dark without QApplication."""
        manager = ThemeManager()
        # Note: In test environment, QApplication may or may not exist
        palette = manager.detect_system_theme()
        assert palette in (DARK_PALETTE, LIGHT_PALETTE)


class TestThemePaletteEdgeCases:
    """Test edge cases for ThemePalette."""

    def test_palette_name_non_hex_background(self) -> None:
        """Test name property with non-hex background color (e.g., rgb)."""
        palette = ThemePalette(
            background="rgb(30, 30, 30)",  # Not a hex color
            surface="",
            surface_hover="",
            surface_selected="",
            surface_dim="",
            surface_elevated="",
            surface_success="",
            surface_error="",
            border="",
            border_selected="",
            text="",
            text_secondary="",
            text_disabled="",
            success="",
            error="",
            warning="",
            accent="",
            accent_hover="",
            scrollbar="",
            scrollbar_hover="",
            slider_groove="",
            slider_fill="",
            slider_handle="",
        )
        # Should return "dark" for non-hex colors (fallback)
        assert palette.name == "dark"


class TestThemeManagerWithApp:
    """Test ThemeManager methods that require QApplication context."""

    def test_apply_theme_none_auto_detects(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test apply_theme(None) auto-detects system theme."""
        manager = ThemeManager()
        manager.apply_theme(None)
        # Should have a valid palette after auto-detection
        assert manager.palette in (DARK_PALETTE, LIGHT_PALETTE)

    def test_connect_system_theme_changes(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test connecting to system theme changes doesn't crash."""
        manager = ThemeManager()
        # Should not raise even if API is not available
        manager.connect_system_theme_changes()

    def test_on_system_theme_changed(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test _on_system_theme_changed handler."""
        manager = ThemeManager()
        # Should not raise
        manager._on_system_theme_changed()
        # Should have a valid palette after re-detection
        assert manager.palette in (DARK_PALETTE, LIGHT_PALETTE)

    def test_global_stylesheet_generation(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test that global stylesheet is generated."""
        manager = ThemeManager()
        stylesheet = manager._global_stylesheet()
        # Should contain expected CSS
        assert "QWidget" in stylesheet
        assert "QLineEdit" in stylesheet
        assert "QScrollBar" in stylesheet


class TestThemeManagerEdgeCases:
    """Test ThemeManager edge cases with mocked Qt APIs."""

    def test_detect_system_theme_no_app(self) -> None:
        """Test detect_system_theme when QGuiApplication is None."""
        manager = ThemeManager()

        with patch("snapctrl.ui.theme.QGuiApplication.instance", return_value=None):
            palette = manager.detect_system_theme()

        assert palette is DARK_PALETTE

    def test_detect_system_theme_light_mode(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test detect_system_theme when system is in light mode."""

        manager = ThemeManager()

        mock_hints = MagicMock()
        mock_hints.colorScheme.return_value = Qt.ColorScheme.Light

        mock_app = MagicMock()
        mock_app.styleHints.return_value = mock_hints

        with patch("snapctrl.ui.theme.QGuiApplication.instance", return_value=mock_app):
            palette = manager.detect_system_theme()

        assert palette is LIGHT_PALETTE

    def test_detect_system_theme_no_color_scheme_api(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test detect_system_theme when colorScheme API is not available."""
        manager = ThemeManager()

        mock_hints = MagicMock()
        mock_hints.colorScheme.side_effect = AttributeError("no colorScheme")

        mock_app = MagicMock()
        mock_app.styleHints.return_value = mock_hints

        with patch("snapctrl.ui.theme.QGuiApplication.instance", return_value=mock_app):
            palette = manager.detect_system_theme()

        assert palette is DARK_PALETTE

    def test_connect_system_theme_changes_no_app(self) -> None:
        """Test connect_system_theme_changes when no app."""
        manager = ThemeManager()

        with patch("snapctrl.ui.theme.QGuiApplication.instance", return_value=None):
            # Should not crash
            manager.connect_system_theme_changes()

    def test_connect_system_theme_changes_no_api(self, qtbot) -> None:  # type: ignore[no-untyped-def]
        """Test connect_system_theme_changes when API not available."""
        manager = ThemeManager()

        mock_hints = MagicMock()
        mock_hints.colorSchemeChanged = MagicMock()
        mock_hints.colorSchemeChanged.connect.side_effect = AttributeError("no signal")

        mock_app = MagicMock()
        mock_app.styleHints.return_value = mock_hints

        with patch("snapctrl.ui.theme.QGuiApplication.instance", return_value=mock_app):
            # Should not crash
            manager.connect_system_theme_changes()
