"""Tests for album art providers."""

import urllib.error
from unittest.mock import MagicMock

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


class TestITunesProviderWithMocks:
    """Tests for iTunes provider with mocked network calls."""

    @pytest.mark.asyncio
    async def test_search_itunes_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful iTunes search."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            return {
                "resultCount": 1,
                "results": [{"artworkUrl100": "http://example.com/100x100.jpg"}],
            }

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_itunes("Test Artist Album")

        assert result == "http://example.com/600x600.jpg"

    @pytest.mark.asyncio
    async def test_search_itunes_no_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test iTunes search with no results."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            return {"resultCount": 0, "results": []}

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_itunes("Unknown Artist")

        assert result == ""

    @pytest.mark.asyncio
    async def test_search_itunes_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test iTunes search with network error."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            raise ConnectionError("Network error")

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_itunes("Artist Album")

        assert result == ""

    @pytest.mark.asyncio
    async def test_download_image_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful image download."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_binary(self: ITunesAlbumArtProvider, url: str) -> bytes:
            return b"fake_image_data"

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider._download_image("http://example.com/image.jpg")

        assert result == b"fake_image_data"

    @pytest.mark.asyncio
    async def test_download_image_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test image download failure."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_binary(self: ITunesAlbumArtProvider, url: str) -> bytes:
            raise ConnectionError("Download failed")

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider._download_image("http://example.com/image.jpg")

        assert result == b""

    @pytest.mark.asyncio
    async def test_fetch_full_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test full fetch flow with mocked network calls."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            return {
                "resultCount": 1,
                "results": [{"artworkUrl100": "http://example.com/100x100.jpg"}],
            }

        def mock_fetch_binary(self: ITunesAlbumArtProvider, url: str) -> bytes:
            return b"image_data"

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)
        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is not None
        assert result.data == b"image_data"
        assert result.source == "iTunes"

    @pytest.mark.asyncio
    async def test_fetch_with_title_fallback(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch uses title when album is empty."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            assert "Test%20Title" in url or "Test+Title" in url or "Test%20" in url
            return {
                "resultCount": 1,
                "results": [{"artworkUrl100": "http://example.com/100x100.jpg"}],
            }

        def mock_fetch_binary(self: ITunesAlbumArtProvider, url: str) -> bytes:
            return b"image_data"

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)
        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider.fetch(artist="Artist", album="", title="Test Title")

        assert result is not None


class TestMusicBrainzProviderWithMocks:
    """Tests for MusicBrainz provider with mocked network calls."""

    @pytest.mark.asyncio
    async def test_search_release_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful MusicBrainz release search."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"releases": [{"id": "12345678-1234-1234-1234-123456789012"}]}

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_release("Artist", "Album")

        assert result == "12345678-1234-1234-1234-123456789012"

    @pytest.mark.asyncio
    async def test_search_release_no_results(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test MusicBrainz search with no results."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"releases": []}

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_release("Unknown", "Album")

        assert result == ""

    @pytest.mark.asyncio
    async def test_search_release_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test MusicBrainz search with network error."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            raise ConnectionError("Network error")

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_release("Artist", "Album")

        assert result == ""

    @pytest.mark.asyncio
    async def test_download_image_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test successful image download from Cover Art Archive."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_binary(self: MusicBrainzAlbumArtProvider, url: str) -> bytes:
            return b"cover_art_data"

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider._download_image("http://coverartarchive.org/test.jpg")

        assert result == b"cover_art_data"

    @pytest.mark.asyncio
    async def test_download_image_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test image download failure."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_binary(self: MusicBrainzAlbumArtProvider, url: str) -> bytes:
            raise ConnectionError("Download failed")

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider._download_image("http://coverartarchive.org/test.jpg")

        assert result == b""

    @pytest.mark.asyncio
    async def test_fetch_full_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test full fetch flow with mocked network calls."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"releases": [{"id": "12345678-1234-1234-1234-123456789012"}]}

        def mock_fetch_binary(self: MusicBrainzAlbumArtProvider, url: str) -> bytes:
            return b"cover_image"

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)
        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is not None
        assert result.data == b"cover_image"
        assert result.source == "MusicBrainz"

    @pytest.mark.asyncio
    async def test_fetch_no_mbid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch returns None when no MBID found."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"releases": []}

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_download_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch returns None when download fails."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"releases": [{"id": "test-id"}]}

        def mock_fetch_binary(self: MusicBrainzAlbumArtProvider, url: str) -> bytes:
            raise ConnectionError("Download failed")

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)
        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_binary", mock_fetch_binary)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None


class TestITunesProviderExtended:
    """Extended tests for iTunes provider."""

    @pytest.mark.asyncio
    async def test_fetch_search_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch returns None when iTunes search returns no results."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            return {"resultCount": 0, "results": []}

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider.fetch(artist="Unknown Artist", album="Unknown Album")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_download_fails(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch returns None when download fails."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            return {
                "resultCount": 1,
                "results": [{"artworkUrl100": "http://example.com/100x100.jpg"}],
            }

        async def mock_download_image(self: ITunesAlbumArtProvider, url: str) -> bytes | None:
            return None  # Simulate download failure

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)
        monkeypatch.setattr(ITunesAlbumArtProvider, "_download_image", mock_download_image)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_no_artwork_url(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch returns None when result has no artwork URL."""
        provider = ITunesAlbumArtProvider()

        def mock_fetch_json(self: ITunesAlbumArtProvider, url: str) -> dict:
            return {
                "resultCount": 1,
                "results": [{}],  # No artworkUrl100
            }

        monkeypatch.setattr(ITunesAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None


class TestMusicBrainzProviderExtended:
    """Extended tests for MusicBrainz provider."""

    @pytest.mark.asyncio
    async def test_search_exception(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search handles exceptions gracefully."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            raise ConnectionError("Network error")

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_empty_releases(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test fetch returns None when releases is empty."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"releases": []}

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None

    @pytest.mark.asyncio
    async def test_search_release_empty_mbid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search_release returns empty when release has no id."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            # Release exists but has no id (or empty id)
            return {"releases": [{"id": ""}]}

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_release("Artist", "Album")

        assert result == ""

    @pytest.mark.asyncio
    async def test_search_release_null_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search_release handles None result from _fetch_json."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict | None:
            return None

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_release("Artist", "Album")

        assert result == ""

    @pytest.mark.asyncio
    async def test_search_release_no_releases_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test search_release handles result without releases key."""
        provider = MusicBrainzAlbumArtProvider()

        def mock_fetch_json(self: MusicBrainzAlbumArtProvider, url: str) -> dict:
            return {"other_key": "value"}  # No 'releases' key

        monkeypatch.setattr(MusicBrainzAlbumArtProvider, "_fetch_json", mock_fetch_json)

        result = await provider._search_release("Artist", "Album")

        assert result == ""


class TestMusicBrainzBlockingMethods:
    """Tests for MusicBrainz blocking HTTP methods."""

    def test_fetch_json_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _fetch_json returns parsed JSON."""
        provider = MusicBrainzAlbumArtProvider()

        # Mock urlopen to return valid JSON
        mock_response = MagicMock()
        mock_response.read.return_value = b'{"releases": [{"id": "test-123"}]}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        def mock_urlopen(request, timeout=None):
            return mock_response

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        result = provider._fetch_json("http://example.com/test")

        assert result == {"releases": [{"id": "test-123"}]}

    def test_fetch_binary_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test _fetch_binary returns raw bytes."""
        provider = MusicBrainzAlbumArtProvider()

        # Mock urlopen to return binary data
        mock_response = MagicMock()
        mock_response.read.return_value = b"\x89PNG\r\n\x1a\n..."
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        def mock_urlopen(request, timeout=None):
            return mock_response

        monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)

        result = provider._fetch_binary("http://example.com/image.png")

        assert result == b"\x89PNG\r\n\x1a\n..."


class TestFallbackProviderErrorHandling:
    """Tests for FallbackAlbumArtProvider error handling."""

    @pytest.mark.asyncio
    async def test_fallback_handles_url_error(self) -> None:
        """Test fallback handles URLError from provider."""

        class FailingProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "Failing"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                raise urllib.error.URLError("Connection refused")

        class SuccessProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "Success"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                return AlbumArt(data=b"success", source="Success")

        provider = FallbackAlbumArtProvider([FailingProvider(), SuccessProvider()])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result is not None
        assert result.data == b"success"

    @pytest.mark.asyncio
    async def test_fallback_handles_timeout_error(self) -> None:
        """Test fallback handles TimeoutError from provider."""

        class TimeoutProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "Timeout"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                raise TimeoutError("Request timed out")

        class SuccessProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "Success"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                return AlbumArt(data=b"success", source="Success")

        provider = FallbackAlbumArtProvider([TimeoutProvider(), SuccessProvider()])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result is not None
        assert result.data == b"success"

    @pytest.mark.asyncio
    async def test_fallback_handles_unexpected_error(self) -> None:
        """Test fallback handles unexpected errors from provider."""

        class BuggyProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "Buggy"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                raise ValueError("Unexpected internal error")

        class SuccessProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "Success"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                return AlbumArt(data=b"success", source="Success")

        provider = FallbackAlbumArtProvider([BuggyProvider(), SuccessProvider()])
        result = await provider.fetch(artist="Artist", album="Album")

        assert result is not None
        assert result.data == b"success"

    @pytest.mark.asyncio
    async def test_fallback_all_providers_network_error(self) -> None:
        """Test fallback returns None when all providers have network errors."""

        class NetworkErrorProvider(AlbumArtProvider):
            @property
            def name(self) -> str:
                return "NetworkError"

            async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
                raise OSError("Network unreachable")

        provider = FallbackAlbumArtProvider(
            [
                NetworkErrorProvider(),
                NetworkErrorProvider(),
            ]
        )
        result = await provider.fetch(artist="Artist", album="Album")

        assert result is None
