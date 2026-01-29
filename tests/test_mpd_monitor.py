"""Tests for MPD metadata monitor."""

import pytest
from PySide6.QtCore import QCoreApplication

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
