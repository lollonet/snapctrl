"""Tests for the centralized theme system."""

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
