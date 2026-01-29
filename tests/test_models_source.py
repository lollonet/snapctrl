"""Tests for Source model."""

import pytest

from snapctrl.models.source import Source


class TestSource:
    """Tests for Source dataclass."""

    def test_source_creation_with_defaults(self) -> None:
        """Test creating a source with default values."""
        source = Source(id="stream-1")
        assert source.id == "stream-1"
        assert source.name == ""
        assert source.status == "idle"
        assert source.stream_type == ""

    def test_source_creation_with_all_params(self) -> None:
        """Test creating a source with all parameters."""
        source = Source(
            id="stream-2",
            name="Spotify",
            status="playing",
            stream_type="spotify",
        )
        assert source.id == "stream-2"
        assert source.name == "Spotify"
        assert source.status == "playing"
        assert source.stream_type == "spotify"

    def test_is_playing_true(self) -> None:
        """Test is_playing returns True when status is playing."""
        source = Source(id="stream-1", status="playing")
        assert source.is_playing is True

    def test_is_playing_false(self) -> None:
        """Test is_playing returns False when not playing."""
        source = Source(id="stream-1", status="idle")
        assert source.is_playing is False

    def test_is_idle_true(self) -> None:
        """Test is_idle returns True when status is idle."""
        source = Source(id="stream-1", status="idle")
        assert source.is_idle is True

    def test_is_idle_false(self) -> None:
        """Test is_idle returns False when not idle."""
        source = Source(id="stream-1", status="playing")
        assert source.is_idle is False

    def test_type_alias(self) -> None:
        """Test type is an alias for stream_type."""
        source = Source(id="stream-1", stream_type="airplay")
        assert source.type == "airplay"

    def test_source_is_immutable(self) -> None:
        """Test that Source instances are immutable (frozen)."""
        source = Source(id="stream-1")
        with pytest.raises(Exception):  # FrozenInstanceError
            source.status = "playing"  # type: ignore[misc]

    def test_source_equality(self) -> None:
        """Test source equality comparison."""
        source1 = Source(id="stream-1", name="Test")
        source2 = Source(id="stream-1", name="Test")
        source3 = Source(id="stream-1", name="Different")

        assert source1 == source2
        assert source1 != source3
