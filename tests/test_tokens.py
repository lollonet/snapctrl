"""Tests for design tokens."""

import pytest

from snapctrl.ui.tokens import (
    SizingTokens,
    SpacingTokens,
    TypographyTokens,
    sizing,
    spacing,
    typography,
)


class TestSpacingTokens:
    """Test spacing token values and immutability."""

    def test_default_values(self) -> None:
        """Test that spacing tokens have expected default values."""
        assert spacing.xxs == 2
        assert spacing.xs == 4
        assert spacing.sm == 8
        assert spacing.md == 12
        assert spacing.lg == 16
        assert spacing.xl == 24

    def test_scale_is_increasing(self) -> None:
        """Test that spacing scale increases monotonically."""
        values = [spacing.xxs, spacing.xs, spacing.sm, spacing.md, spacing.lg, spacing.xl]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], f"spacing scale not increasing at index {i}"

    def test_frozen(self) -> None:
        """Test that spacing tokens are immutable."""
        with pytest.raises(AttributeError):
            spacing.sm = 999  # type: ignore[misc]

    def test_is_singleton_instance(self) -> None:
        """Test that module-level spacing is a SpacingTokens instance."""
        assert isinstance(spacing, SpacingTokens)


class TestTypographyTokens:
    """Test typography token values and immutability."""

    def test_default_values(self) -> None:
        """Test that typography tokens have expected default values."""
        assert typography.caption == 8
        assert typography.small == 9
        assert typography.body == 10
        assert typography.subtitle == 11
        assert typography.title == 12
        assert typography.heading == 14

    def test_scale_is_increasing(self) -> None:
        """Test that typography scale increases monotonically."""
        values = [
            typography.caption,
            typography.small,
            typography.body,
            typography.subtitle,
            typography.title,
            typography.heading,
        ]
        for i in range(len(values) - 1):
            assert values[i] < values[i + 1], f"typography scale not increasing at index {i}"

    def test_frozen(self) -> None:
        """Test that typography tokens are immutable."""
        with pytest.raises(AttributeError):
            typography.body = 999  # type: ignore[misc]

    def test_is_singleton_instance(self) -> None:
        """Test that module-level typography is a TypographyTokens instance."""
        assert isinstance(typography, TypographyTokens)


class TestSizingTokens:
    """Test sizing token values and immutability."""

    def test_border_radius_values(self) -> None:
        """Test border radius tokens."""
        assert sizing.border_radius_sm == 2
        assert sizing.border_radius_md == 4
        assert sizing.border_radius_lg == 8

    def test_icon_size_values(self) -> None:
        """Test icon size tokens."""
        assert sizing.icon_sm == 16
        assert sizing.icon_md == 24
        assert sizing.icon_lg == 32

    def test_emoji_sizes(self) -> None:
        """Test emoji/icon font sizing tokens."""
        assert sizing.emoji_indicator == 14
        assert sizing.emoji_button == 16

    def test_scrollbar_sizes(self) -> None:
        """Test scrollbar sizing tokens."""
        assert sizing.scrollbar_width == 8
        assert sizing.scrollbar_min_handle == 20

    def test_component_sizes(self) -> None:
        """Test component-specific sizing tokens."""
        assert sizing.album_art == 80
        assert sizing.control_button == 32
        assert sizing.panel_min_side == 150
        assert sizing.panel_max_side == 300

    def test_frozen(self) -> None:
        """Test that sizing tokens are immutable."""
        with pytest.raises(AttributeError):
            sizing.icon_md = 999  # type: ignore[misc]

    def test_is_singleton_instance(self) -> None:
        """Test that module-level sizing is a SizingTokens instance."""
        assert isinstance(sizing, SizingTokens)

    def test_border_radius_scale_increasing(self) -> None:
        """Test that border radius scale increases."""
        assert sizing.border_radius_sm < sizing.border_radius_md < sizing.border_radius_lg

    def test_icon_scale_increasing(self) -> None:
        """Test that icon size scale increases."""
        assert sizing.icon_sm < sizing.icon_md < sizing.icon_lg
