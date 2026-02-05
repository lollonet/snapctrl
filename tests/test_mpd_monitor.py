"""Tests for MPD metadata monitor."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from PySide6.QtCore import QCoreApplication

from snapctrl.api.album_art import AlbumArt
from snapctrl.api.mpd import MpdError
from snapctrl.api.mpd.types import MpdStatus, MpdTrack
from snapctrl.core.mpd_monitor import (
    DEFAULT_ART_CACHE_SIZE,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RECONNECT_DELAY,
    MpdMonitor,
)


@pytest.fixture
def qapp() -> QCoreApplication:
    """Create a Qt application for testing."""
    app = QCoreApplication.instance()
    if app is None:
        app = QCoreApplication([])
    return app


@pytest.fixture
def monitor(qapp: QCoreApplication) -> MpdMonitor:
    """Create an MpdMonitor for testing."""
    return MpdMonitor("192.168.1.100", port=6600)


class TestMpdMonitorInit:
    """Tests for MpdMonitor initialization."""

    def test_init_defaults(self, qapp: QCoreApplication) -> None:
        """Test MpdMonitor initialization with defaults."""
        monitor = MpdMonitor("localhost")
        assert monitor.host == "localhost"
        assert monitor.port == 6600
        assert monitor._password == ""
        assert monitor._poll_interval == DEFAULT_POLL_INTERVAL
        assert not monitor._running

    def test_init_custom(self, qapp: QCoreApplication) -> None:
        """Test MpdMonitor initialization with custom values."""
        monitor = MpdMonitor(
            "192.168.1.100",
            port=6601,
            password="secret",
            poll_interval=5.0,
        )
        assert monitor.host == "192.168.1.100"
        assert monitor.port == 6601
        assert monitor._password == "secret"
        assert monitor._poll_interval == 5.0

    def test_set_host(self, monitor: MpdMonitor) -> None:
        """Test updating host."""
        monitor.set_host("192.168.1.200", 6601)
        assert monitor.host == "192.168.1.200"
        assert monitor.port == 6601

    def test_set_poll_interval(self, monitor: MpdMonitor) -> None:
        """Test updating poll interval."""
        monitor.set_poll_interval(10.0)
        assert monitor._poll_interval == 10.0


class TestMpdMonitorTrackChange:
    """Tests for track change detection."""

    def test_emit_if_track_changed_none_to_none(self, monitor: MpdMonitor) -> None:
        """Test no emit when both are None."""
        monitor._last_track = None
        assert not monitor._emit_if_track_changed(None)

    def test_emit_if_track_changed_none_to_track(self, monitor: MpdMonitor) -> None:
        """Test emit when track appears."""
        monitor._last_track = None
        track = MpdTrack(file="test.mp3", title="Test")
        assert monitor._emit_if_track_changed(track)
        assert monitor._last_track == track

    def test_emit_if_track_changed_track_to_none(self, monitor: MpdMonitor) -> None:
        """Test emit when track disappears."""
        monitor._last_track = MpdTrack(file="test.mp3")
        assert monitor._emit_if_track_changed(None)
        assert monitor._last_track is None

    def test_emit_if_track_changed_same_track(self, monitor: MpdMonitor) -> None:
        """Test no emit when track is same."""
        track = MpdTrack(file="test.mp3", id=1, title="Test", artist="Artist", album="Album")
        monitor._last_track = track
        assert not monitor._emit_if_track_changed(track)

    def test_emit_if_track_changed_different_file(self, monitor: MpdMonitor) -> None:
        """Test emit when file changes."""
        monitor._last_track = MpdTrack(file="test1.mp3", id=1)
        new_track = MpdTrack(file="test2.mp3", id=2)
        assert monitor._emit_if_track_changed(new_track)
        assert monitor._last_track == new_track

    def test_emit_if_track_changed_different_id(self, monitor: MpdMonitor) -> None:
        """Test emit when ID changes (same file, different position)."""
        monitor._last_track = MpdTrack(file="test.mp3", id=1)
        new_track = MpdTrack(file="test.mp3", id=2)
        assert monitor._emit_if_track_changed(new_track)

    def test_emit_if_track_changed_metadata_update(self, monitor: MpdMonitor) -> None:
        """Test emit when metadata changes on same file."""
        monitor._last_track = MpdTrack(file="test.mp3", id=1, title="Old Title")
        new_track = MpdTrack(file="test.mp3", id=1, title="New Title")
        assert monitor._emit_if_track_changed(new_track)

    def test_emit_if_track_changed_artist_update(self, monitor: MpdMonitor) -> None:
        """Test emit when artist changes."""
        monitor._last_track = MpdTrack(file="test.mp3", id=1, artist="Old Artist")
        new_track = MpdTrack(file="test.mp3", id=1, artist="New Artist")
        assert monitor._emit_if_track_changed(new_track)

    def test_emit_if_track_changed_album_update(self, monitor: MpdMonitor) -> None:
        """Test emit when album changes."""
        monitor._last_track = MpdTrack(file="test.mp3", id=1, album="Old Album")
        new_track = MpdTrack(file="test.mp3", id=1, album="New Album")
        assert monitor._emit_if_track_changed(new_track)


class TestMpdMonitorStatusChange:
    """Tests for status change detection."""

    def test_emit_if_status_changed_first_status(self, monitor: MpdMonitor) -> None:
        """Test emit on first status."""
        status = MpdStatus(state="play", volume=50)
        assert monitor._emit_if_status_changed(status)
        assert monitor._last_status == status

    def test_emit_if_status_changed_same_status(self, monitor: MpdMonitor) -> None:
        """Test no emit when status is same."""
        status = MpdStatus(state="play", volume=50)
        monitor._last_status = status
        assert not monitor._emit_if_status_changed(status)

    def test_emit_if_status_changed_different_status(self, monitor: MpdMonitor) -> None:
        """Test emit when status changes."""
        monitor._last_status = MpdStatus(state="play")
        new_status = MpdStatus(state="pause")
        assert monitor._emit_if_status_changed(new_status)
        assert monitor._last_status == new_status


class TestMpdMonitorArtCache:
    """Tests for album art caching."""

    def test_cache_art(self, monitor: MpdMonitor) -> None:
        """Test caching album art."""
        monitor._cache_art("test.mp3", b"image_data", "image/jpeg")
        assert "test.mp3" in monitor._art_cache
        assert monitor._art_cache["test.mp3"] == (b"image_data", "image/jpeg")

    def test_cache_eviction(self, monitor: MpdMonitor) -> None:
        """Test cache eviction when full."""
        # Fill the cache
        for i in range(DEFAULT_ART_CACHE_SIZE):
            monitor._cache_art(f"file{i}.mp3", b"data", "image/jpeg")

        # Add one more to trigger eviction
        monitor._cache_art("new.mp3", b"new_data", "image/jpeg")

        # First entry should be evicted
        assert "file0.mp3" not in monitor._art_cache
        # New entry should be present
        assert "new.mp3" in monitor._art_cache
        # Cache should not exceed max size
        assert len(monitor._art_cache) == DEFAULT_ART_CACHE_SIZE

    def test_clear_cache(self, monitor: MpdMonitor) -> None:
        """Test clearing the cache."""
        monitor._cache_art("test.mp3", b"data", "image/jpeg")
        monitor._last_art_uri = "test.mp3"

        monitor.clear_cache()

        assert len(monitor._art_cache) == 0
        assert monitor._last_art_uri == ""


class TestMpdMonitorStartStop:
    """Tests for starting and stopping the monitor."""

    def test_start_creates_thread(self, monitor: MpdMonitor) -> None:
        """Test that start creates a background thread."""
        assert monitor._thread is None
        monitor._host = ""  # Invalid host to prevent actual connection
        monitor.start()
        assert monitor._running
        assert monitor._thread is not None
        monitor.stop()

    def test_stop_joins_thread(self, monitor: MpdMonitor) -> None:
        """Test that stop joins the thread."""
        monitor._host = ""  # Invalid host
        monitor.start()
        monitor.stop()
        assert not monitor._running
        assert monitor._thread is None

    def test_start_idempotent(self, monitor: MpdMonitor) -> None:
        """Test that multiple starts don't create multiple threads."""
        monitor._host = ""
        monitor.start()
        thread1 = monitor._thread
        monitor.start()  # Should be no-op
        assert monitor._thread is thread1
        monitor.stop()


class TestConstants:
    """Tests for module constants."""

    def test_default_poll_interval(self) -> None:
        """Test default poll interval."""
        assert DEFAULT_POLL_INTERVAL == 2.0

    def test_default_reconnect_delay(self) -> None:
        """Test default reconnect delay."""
        assert DEFAULT_RECONNECT_DELAY == 5.0

    def test_default_art_cache_size(self) -> None:
        """Test default art cache size."""
        assert DEFAULT_ART_CACHE_SIZE == 10


class TestMpdMonitorAsyncMethods:
    """Tests for MpdMonitor async methods."""

    @pytest.mark.asyncio
    async def test_sleep_interruptible_stops_when_not_running(self, monitor: MpdMonitor) -> None:
        """Test _sleep_interruptible exits when _running is False."""
        monitor._running = False

        # Should return quickly even with long sleep time
        start = asyncio.get_event_loop().time()
        await monitor._sleep_interruptible(10.0)
        elapsed = asyncio.get_event_loop().time() - start

        # Should take less than 1 second (not the full 10 seconds)
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_sleep_interruptible_waits_when_running(self, monitor: MpdMonitor) -> None:
        """Test _sleep_interruptible waits when _running is True."""
        monitor._running = True

        # Sleep for a short time
        start = asyncio.get_event_loop().time()
        await monitor._sleep_interruptible(0.2)
        elapsed = asyncio.get_event_loop().time() - start

        # Should wait approximately the requested time
        assert elapsed >= 0.15  # Allow some tolerance

    @pytest.mark.asyncio
    async def test_poll_status_emits_status(self, monitor: MpdMonitor) -> None:
        """Test _poll_status emits status_changed signal."""
        status_received: list[MpdStatus] = []
        monitor.status_changed.connect(status_received.append)

        mock_client = MagicMock()
        mock_status = MpdStatus(state="play", volume=75)
        mock_client.status = AsyncMock(return_value=mock_status)
        mock_client.currentsong = AsyncMock(return_value=None)

        await monitor._poll_status(mock_client)

        assert len(status_received) == 1
        assert status_received[0] == mock_status

    @pytest.mark.asyncio
    async def test_poll_status_emits_track(self, monitor: MpdMonitor) -> None:
        """Test _poll_status emits track_changed signal."""
        tracks_received: list[MpdTrack | None] = []
        monitor.track_changed.connect(tracks_received.append)

        mock_client = MagicMock()
        mock_status = MpdStatus(state="play")
        mock_track = MpdTrack(file="test.mp3", title="Test Song")
        mock_client.status = AsyncMock(return_value=mock_status)
        mock_client.currentsong = AsyncMock(return_value=mock_track)
        mock_client.get_album_art = AsyncMock(return_value=None)

        await monitor._poll_status(mock_client)

        assert len(tracks_received) == 1
        assert tracks_received[0] == mock_track

    @pytest.mark.asyncio
    async def test_poll_status_handles_mpd_error(self, monitor: MpdMonitor) -> None:
        """Test _poll_status handles MpdError gracefully."""
        mock_client = MagicMock()
        mock_client.status = AsyncMock(side_effect=MpdError(50, "status", "protocol error"))

        # Should not raise
        await monitor._poll_status(mock_client)

    @pytest.mark.asyncio
    async def test_fetch_album_art_from_cache(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art returns cached art."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        # Pre-cache art
        monitor._art_cache["test.mp3"] = (b"cached_data", "image/png")
        monitor._last_art_uri = ""  # Different from what we're requesting

        mock_client = MagicMock()
        track = MpdTrack(file="test.mp3", artist="Artist", album="Album")

        await monitor._fetch_album_art(mock_client, track)

        # Should emit cached art
        assert len(art_received) == 1
        assert art_received[0] == ("test.mp3", b"cached_data", "image/png")
        assert monitor._last_art_uri == "test.mp3"

    @pytest.mark.asyncio
    async def test_fetch_album_art_from_mpd(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art gets art from MPD."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        mock_client = MagicMock()
        mock_art = AlbumArt(data=b"mpd_art_data", mime_type="image/jpeg")
        mock_client.get_album_art = AsyncMock(return_value=mock_art)

        track = MpdTrack(file="new.mp3", artist="Artist", album="Album")

        await monitor._fetch_album_art(mock_client, track)

        assert len(art_received) == 1
        assert art_received[0] == ("new.mp3", b"mpd_art_data", "image/jpeg")
        # Should be cached
        assert "new.mp3" in monitor._art_cache

    @pytest.mark.asyncio
    async def test_fetch_album_art_mpd_fails_tries_fallback(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art falls back to external providers."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        mock_client = MagicMock()
        # MPD art fails
        mock_client.get_album_art = AsyncMock(side_effect=MpdError(50, "readpicture", "no art"))

        # Mock fallback provider to return art
        fallback_art = AlbumArt(data=b"fallback_data", mime_type="image/png", source="iTunes")
        with patch.object(monitor._art_provider, "fetch", return_value=fallback_art) as mock_fetch:
            track = MpdTrack(file="track.mp3", artist="Artist", album="Album", title="Song")
            await monitor._fetch_album_art(mock_client, track)

            mock_fetch.assert_called_once_with(artist="Artist", album="Album", title="Song")

        assert len(art_received) == 1
        assert art_received[0][1] == b"fallback_data"

    @pytest.mark.asyncio
    async def test_fetch_album_art_no_art_available(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art emits empty when no art found."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        mock_client = MagicMock()
        mock_client.get_album_art = AsyncMock(side_effect=MpdError(50, "readpicture", "no art"))

        # Fallback also returns nothing
        with patch.object(monitor._art_provider, "fetch", return_value=None):
            track = MpdTrack(file="noart.mp3", artist="Artist", album="Album")
            await monitor._fetch_album_art(mock_client, track)

        # Should emit empty art
        assert len(art_received) == 1
        assert art_received[0] == ("noart.mp3", b"", "")

    @pytest.mark.asyncio
    async def test_fetch_album_art_no_artist_skips_fallback(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art skips fallback when no artist."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        mock_client = MagicMock()
        mock_client.get_album_art = AsyncMock(return_value=None)

        # Should not call fallback because no artist
        with patch.object(monitor._art_provider, "fetch") as mock_fetch:
            track = MpdTrack(file="noartist.mp3", artist="", album="")
            await monitor._fetch_album_art(mock_client, track)
            mock_fetch.assert_not_called()

        # Should emit empty art
        assert len(art_received) == 1
        assert art_received[0] == ("noartist.mp3", b"", "")

    @pytest.mark.asyncio
    async def test_fetch_album_art_fallback_network_error(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art handles fallback network errors."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        mock_client = MagicMock()
        mock_client.get_album_art = AsyncMock(side_effect=MpdError(50, "readpicture", "no art"))

        # Fallback throws network error
        with patch.object(monitor._art_provider, "fetch", side_effect=OSError("network down")):
            track = MpdTrack(file="error.mp3", artist="Artist", album="Album")
            await monitor._fetch_album_art(mock_client, track)

        # Should emit empty art after error
        assert len(art_received) == 1
        assert art_received[0] == ("error.mp3", b"", "")

    @pytest.mark.asyncio
    async def test_fetch_album_art_fallback_unexpected_error(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art handles unexpected fallback errors."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        mock_client = MagicMock()
        mock_client.get_album_art = AsyncMock(side_effect=MpdError(50, "readpicture", "no art"))

        # Fallback throws unexpected error
        with patch.object(monitor._art_provider, "fetch", side_effect=ValueError("unexpected")):
            track = MpdTrack(file="unexpected.mp3", artist="Artist", album="Album")
            await monitor._fetch_album_art(mock_client, track)

        # Should emit empty art after error
        assert len(art_received) == 1
        assert art_received[0] == ("unexpected.mp3", b"", "")


class TestMpdMonitorCacheHit:
    """Tests for cache hit scenarios."""

    @pytest.mark.asyncio
    async def test_fetch_album_art_cache_same_uri_no_emit(self, monitor: MpdMonitor) -> None:
        """Test _fetch_album_art doesn't re-emit when URI matches last."""
        art_received: list[tuple[str, bytes, str]] = []
        monitor.art_changed.connect(lambda uri, data, mime: art_received.append((uri, data, mime)))

        # Pre-cache art and set last_art_uri to same value
        monitor._art_cache["same.mp3"] = (b"cached", "image/jpeg")
        monitor._last_art_uri = "same.mp3"

        mock_client = MagicMock()
        track = MpdTrack(file="same.mp3", artist="Artist")

        await monitor._fetch_album_art(mock_client, track)

        # Should NOT emit since URI matches last
        assert len(art_received) == 0
