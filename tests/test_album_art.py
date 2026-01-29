"""Tests for album art providers."""

import pytest

from snapctrl.api.album_art import (
    AlbumArt,
    AlbumArtProvider,
    FallbackAlbumArtProvider,
    ITunesAlbumArtProvider,
    MusicBrainzAlbumArtProvider,
)


class TestAlbumArt:
    """Tests for AlbumArt dataclass."""

    def test_creation(self) -> None:
        """Test basic creation."""
        art = AlbumArt(data=b"test", mime_type="image/jpeg")
        assert art.data == b"test"
        assert art.mime_type == "image/jpeg"
        assert art.url == ""
        assert art.source == ""

    def test_with_all_fields(self) -> None:
        """Test creation with all fields."""
        art = AlbumArt(
            data=b"test",
            mime_type="image/png",
            url="http://example.com/art.png",
            source="iTunes",
        )
        assert art.data == b"test"
        assert art.mime_type == "image/png"
        assert art.url == "http://example.com/art.png"
        assert art.source == "iTunes"

    def test_is_valid_with_data(self) -> None:
        """Test is_valid returns True when data present."""
        art = AlbumArt(data=b"test")
        assert art.is_valid is True

    def test_is_valid_empty_data(self) -> None:
        """Test is_valid returns False when data empty."""
        art = AlbumArt(data=b"")
        assert art.is_valid is False


class TestITunesProvider:
    """Tests for iTunes album art provider."""

    def test_name(self) -> None:
        """Test provider name."""
        provider = ITunesAlbumArtProvider()
        assert provider.name == "iTunes"

    @pytest.mark.asyncio
    async def test_fetch_no_artist(self) -> None:
        """Test fetch returns None without artist."""
        provider = ITunesAlbumArtProvider()
        result = await provider.fetch(artist="", album="Test Album")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_no_album_or_title(self) -> None:
        """Test fetch returns None without album or title."""
        provider = ITunesAlbumArtProvider()
        result = await provider.fetch(artist="Test Artist", album="", title="")
        assert result is None


class TestMusicBrainzProvider:
    """Tests for MusicBrainz album art provider."""

    def test_name(self) -> None:
        """Test provider name."""
        provider = MusicBrainzAlbumArtProvider()
        assert provider.name == "MusicBrainz"

    @pytest.mark.asyncio
    async def test_fetch_no_artist(self) -> None:
        """Test fetch returns None without artist."""
        provider = MusicBrainzAlbumArtProvider()
        result = await provider.fetch(artist="", album="Test Album")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_no_album(self) -> None:
        """Test fetch returns None without album (MusicBrainz needs album)."""
        provider = MusicBrainzAlbumArtProvider()
        result = await provider.fetch(artist="Test Artist", album="", title="Test Song")
        assert result is None


class MockProvider(AlbumArtProvider):
    """Mock provider for testing fallback chain."""

    def __init__(self, name: str, return_art: AlbumArt | None = None) -> None:
        self._name = name
        self._return_art = return_art
        self.fetch_count = 0

    @property
    def name(self) -> str:
        return self._name

    async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
        self.fetch_count += 1
        return self._return_art


class TestFallbackProvider:
    """Tests for fallback album art provider."""

    def test_name(self) -> None:
        """Test fallback provider name combines children."""
        provider = FallbackAlbumArtProvider(
            [
                MockProvider("A"),
                MockProvider("B"),
            ]
        )
        assert provider.name == "Fallback(A, B)"

    @pytest.mark.asyncio
    async def test_fetch_no_artist(self) -> None:
        """Test fetch returns None without artist."""
        provider = FallbackAlbumArtProvider([MockProvider("Test")])
        result = await provider.fetch(artist="", album="Album")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_first_success(self) -> None:
        """Test fetch stops at first successful provider."""
        art = AlbumArt(data=b"test", source="A")
        p1 = MockProvider("A", return_art=art)
        p2 = MockProvider("B", return_art=AlbumArt(data=b"other", source="B"))

        provider = FallbackAlbumArtProvider([p1, p2])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result == art
        assert p1.fetch_count == 1
        assert p2.fetch_count == 0  # Never called

    @pytest.mark.asyncio
    async def test_fetch_fallback_on_none(self) -> None:
        """Test fetch tries next provider when first returns None."""
        art = AlbumArt(data=b"test", source="B")
        p1 = MockProvider("A", return_art=None)
        p2 = MockProvider("B", return_art=art)

        provider = FallbackAlbumArtProvider([p1, p2])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result == art
        assert p1.fetch_count == 1
        assert p2.fetch_count == 1

    @pytest.mark.asyncio
    async def test_fetch_fallback_on_invalid(self) -> None:
        """Test fetch tries next provider when first returns invalid art."""
        invalid_art = AlbumArt(data=b"", source="A")  # Empty data = invalid
        valid_art = AlbumArt(data=b"test", source="B")
        p1 = MockProvider("A", return_art=invalid_art)
        p2 = MockProvider("B", return_art=valid_art)

        provider = FallbackAlbumArtProvider([p1, p2])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result == valid_art
        assert p1.fetch_count == 1
        assert p2.fetch_count == 1

    @pytest.mark.asyncio
    async def test_fetch_all_fail(self) -> None:
        """Test fetch returns None when all providers fail."""
        p1 = MockProvider("A", return_art=None)
        p2 = MockProvider("B", return_art=None)

        provider = FallbackAlbumArtProvider([p1, p2])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None
        assert p1.fetch_count == 1
        assert p2.fetch_count == 1


class TestProviderExports:
    """Test module exports are correct."""

    def test_all_providers_exported(self) -> None:
        """Test all providers are exported from module."""
        # Verify all expected classes are importable
        assert AlbumArt is not None
        assert AlbumArtProvider is not None
        assert FallbackAlbumArtProvider is not None
        assert ITunesAlbumArtProvider is not None
        assert MusicBrainzAlbumArtProvider is not None
