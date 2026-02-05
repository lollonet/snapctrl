"""Tests for SourcesPanel."""

from __future__ import annotations

import base64
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import QBuffer, QEvent, QIODevice
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QListWidgetItem
from pytestqt.qtbot import QtBot

from snapctrl.models.source import Source, SourceStatus
from snapctrl.ui.panels.sources import MAX_ALBUM_ART_B64_SIZE, SourcesPanel


@pytest.fixture
def idle_source() -> Source:
    """Create an idle source for testing."""
    return Source(id="s1", name="Test Source", status=SourceStatus.IDLE)


@pytest.fixture
def playing_source() -> Source:
    """Create a playing source for testing."""
    return Source(
        id="s2",
        name="Playing Source",
        status=SourceStatus.PLAYING,
        meta_title="Song Title",
        meta_artist="Artist Name",
        meta_album="Album Name",
    )


class TestSourcesPanelCreation:
    """Test panel creation."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test panel can be created."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)
        assert panel is not None

    def test_has_signals(self, qtbot: QtBot) -> None:
        """Test panel has required signals."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "source_selected")

    def test_initial_state(self, qtbot: QtBot) -> None:
        """Test panel starts with empty source list."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._sources == []


class TestSourcesDisplay:
    """Test sources display functionality."""

    def test_set_sources(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test setting sources populates list."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])

        # Check internal list is updated
        assert len(panel._sources) == 1
        assert panel._sources[0].id == "s1"

    def test_set_sources_multiple(
        self, qtbot: QtBot, idle_source: Source, playing_source: Source
    ) -> None:
        """Test setting multiple sources."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source, playing_source])

        assert len(panel._sources) == 2

    def test_set_sources_empty(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test clearing sources."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        panel.set_sources([])

        assert len(panel._sources) == 0

    def test_set_sources_updates_list_widget(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test set_sources updates the list widget."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])

        # The list widget should have an item
        assert panel._list.count() == 1


class TestSourceSelection:
    """Test source selection functionality."""

    def test_source_selected_signal(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test source_selected signal is emitted."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])

        received: list[str] = []
        panel.source_selected.connect(received.append)

        # Simulate selection change
        panel._list.setCurrentRow(0)
        # Note: Selection change requires list widget interaction

    def test_select_source_by_id(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test programmatic source selection."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])

        # Try to select the source
        panel._list.setCurrentRow(0)
        # Verify selection happened
        assert panel._list.currentRow() == 0


class TestNowPlayingDisplay:
    """Test now playing display."""

    def test_sources_with_metadata(self, qtbot: QtBot, playing_source: Source) -> None:
        """Test source with metadata can be set."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([playing_source])

        # Verify source is stored
        assert len(panel._sources) == 1
        assert panel._sources[0].meta_artist == "Artist Name"
        assert panel._sources[0].meta_title == "Song Title"

    def test_sources_metadata_changes(
        self, qtbot: QtBot, playing_source: Source, idle_source: Source
    ) -> None:
        """Test updating sources clears old metadata."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([playing_source])
        panel.set_sources([idle_source])

        # First source should be replaced
        assert len(panel._sources) == 1
        assert panel._sources[0].meta_artist == ""


class TestServerHost:
    """Test server host configuration."""

    def test_set_server_host(self, qtbot: QtBot) -> None:
        """Test setting server host for URL rewriting."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_server_host("192.168.1.100")

        assert panel._server_host == "192.168.1.100"


class TestTheme:
    """Test theme functionality."""

    def test_refresh_theme(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test theme refresh doesn't crash."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        panel.refresh_theme()  # Should not crash


class TestAlbumArtHandling:
    """Test album art handling."""

    def test_art_loaded_flag_initial(self, qtbot: QtBot) -> None:
        """Test art_loaded flag starts as False."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._art_loaded is False

    def test_pending_art_url_initial(self, qtbot: QtBot) -> None:
        """Test pending art URL starts empty."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._pending_art_url == ""

    def test_has_network_manager(self, qtbot: QtBot) -> None:
        """Test panel has network manager for HTTP art."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._network_manager is not None


class TestWidgetCreation:
    """Test widget hierarchy."""

    def test_has_list_widget(self, qtbot: QtBot) -> None:
        """Test panel has list widget."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "_list")
        assert panel._list is not None

    def test_resize_timer_exists(self, qtbot: QtBot) -> None:
        """Test panel has resize debounce timer."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "_resize_timer")
        assert panel._resize_timer is not None


class TestItemDoubleClick:
    """Test double-click handling."""

    def test_double_click_emits_signal(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test double-clicking item emits source_selected signal."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])

        received: list[str] = []
        panel.source_selected.connect(received.append)

        # Simulate double-click via internal handler
        item = panel._list.item(0)
        panel._on_item_double_clicked(item)

        assert received == ["s1"]

    def test_double_click_no_id(self, qtbot: QtBot) -> None:
        """Test double-click with item that has no user data."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        received: list[str] = []
        panel.source_selected.connect(received.append)

        # Create item without user data
        item = QListWidgetItem("Test")
        panel._on_item_double_clicked(item)

        assert received == []


class TestSelectionChanged:
    """Test selection change handling."""

    def test_selection_updates_details(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test selecting source updates details data."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        panel._list.setCurrentRow(0)

        # Check that details were updated (status label should have content)
        assert "Idle" in panel._detail_status.text()

    def test_no_selection_clears_via_handler(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test clearing selection via handler."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        panel._list.setCurrentRow(0)

        # Manually call handler with None
        panel._on_selection_changed(None, None)
        # Handler should have hidden details (but we can't verify isVisible without show)


class TestGetSourceById:
    """Test _get_source_by_id method."""

    def test_find_existing_source(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test finding existing source by ID."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        found = panel._get_source_by_id("s1")

        assert found is not None
        assert found.id == "s1"

    def test_find_nonexistent_source(self, qtbot: QtBot) -> None:
        """Test finding nonexistent source returns None."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        found = panel._get_source_by_id("nonexistent")

        assert found is None


class TestPrivateIP:
    """Test _is_private_ip method."""

    def test_localhost(self, qtbot: QtBot) -> None:
        """Test localhost is private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("localhost") is True

    def test_localhost_localdomain(self, qtbot: QtBot) -> None:
        """Test localhost.localdomain is private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("localhost.localdomain") is True

    def test_loopback_ip(self, qtbot: QtBot) -> None:
        """Test loopback IP is private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("127.0.0.1") is True

    def test_private_ip_192(self, qtbot: QtBot) -> None:
        """Test 192.168.x.x is private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("192.168.1.100") is True

    def test_private_ip_10(self, qtbot: QtBot) -> None:
        """Test 10.x.x.x is private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("10.0.0.1") is True

    def test_public_ip(self, qtbot: QtBot) -> None:
        """Test public IP is not private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("8.8.8.8") is False

    def test_local_domain(self, qtbot: QtBot) -> None:
        """Test .local domain is private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("myserver.local") is True

    def test_public_domain(self, qtbot: QtBot) -> None:
        """Test public domain is not private."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel._is_private_ip("example.com") is False


class TestFormatTime:
    """Test _format_time static method."""

    def test_format_seconds(self) -> None:
        """Test formatting seconds under a minute."""
        assert SourcesPanel._format_time(45) == "0:45"

    def test_format_minutes(self) -> None:
        """Test formatting minutes."""
        assert SourcesPanel._format_time(125) == "2:05"

    def test_format_hours(self) -> None:
        """Test formatting hours."""
        assert SourcesPanel._format_time(3725) == "1:02:05"

    def test_format_zero(self) -> None:
        """Test formatting zero."""
        assert SourcesPanel._format_time(0) == "0:00"


class TestPlaybackStatus:
    """Test playback status display."""

    def test_set_playback_status_playing(self, qtbot: QtBot) -> None:
        """Test setting playback status while playing."""
        panel = SourcesPanel()
        panel.show()  # Must show for visibility to work
        qtbot.addWidget(panel)

        panel.set_playback_status(elapsed=60.0, duration=180.0, state="play")

        assert "1:00" in panel._time_label.text()
        assert "3:00" in panel._time_label.text()
        # Progress bar should have value set
        assert panel._progress_bar.value() > 0

    def test_set_playback_status_paused(self, qtbot: QtBot) -> None:
        """Test setting playback status while paused."""
        panel = SourcesPanel()
        panel.show()
        qtbot.addWidget(panel)

        panel.set_playback_status(elapsed=30.0, duration=120.0, state="pause")

        # Time label should have content
        assert "0:30" in panel._time_label.text()

    def test_set_playback_status_stopped(self, qtbot: QtBot) -> None:
        """Test setting playback status while stopped."""
        panel = SourcesPanel()
        panel.show()
        qtbot.addWidget(panel)

        panel.set_playback_status(elapsed=0.0, duration=0.0, state="stop")

        # Progress bar should be at 0
        assert panel._progress_bar.value() == 0

    def test_set_playback_status_zero_duration(self, qtbot: QtBot) -> None:
        """Test playback status with zero duration."""
        panel = SourcesPanel()
        panel.show()
        qtbot.addWidget(panel)

        panel.set_playback_status(elapsed=0.0, duration=0.0, state="play")

        # With zero duration, progress should stay at 0
        assert panel._progress_bar.value() == 0


class TestGetSelectedSourceId:
    """Test get_selected_source_id method."""

    def test_with_selection(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test getting selected source ID."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        panel._list.setCurrentRow(0)

        assert panel.get_selected_source_id() == "s1"

    def test_without_selection(self, qtbot: QtBot) -> None:
        """Test getting source ID when nothing selected."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        assert panel.get_selected_source_id() is None


class TestClearSources:
    """Test clear_sources method."""

    def test_clear_sources(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test clearing sources."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])
        assert panel._list.count() == 1

        panel.clear_sources()
        assert panel._list.count() == 0


class TestUpdateDetails:
    """Test _update_details method."""

    def test_update_details_idle_source(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test updating details for idle source."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(idle_source)

        assert "Idle" in panel._detail_status.text()
        # No metadata, so metadata fields should be cleared
        assert panel._current_artist == ""

    def test_update_details_playing_source(self, qtbot: QtBot, playing_source: Source) -> None:
        """Test updating details for playing source."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(playing_source)

        assert "Playing" in panel._detail_status.text()
        assert panel._current_artist == "Artist Name"
        assert panel._current_title == "Song Title"

    def test_update_details_with_codec(self, qtbot: QtBot) -> None:
        """Test updating details shows codec."""
        source = Source(
            id="s1",
            name="Test",
            status=SourceStatus.IDLE,
            codec="flac",
        )
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(source)

        assert "flac" in panel._detail_codec.text()

    def test_update_details_with_format(self, qtbot: QtBot) -> None:
        """Test updating details shows format."""
        source = Source(
            id="s1",
            name="Test",
            status=SourceStatus.IDLE,
            sample_format="48000:16:2",
        )
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(source)

        # Format label should have the formatted text
        assert "48kHz" in panel._detail_format.text()

    def test_update_details_no_format(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test updating details with empty format."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(idle_source)

        # Format label should be empty when no format
        assert panel._detail_format.text() == "" or "Format:" not in panel._detail_format.text()

    def test_update_details_no_album(self, qtbot: QtBot) -> None:
        """Test updating details with title/artist but no album."""
        source = Source(
            id="s1",
            name="Test",
            status=SourceStatus.PLAYING,
            meta_title="Song",
            meta_artist="Artist",
            meta_album="",
        )
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(source)

        assert panel._current_album == ""
        assert "Song" in panel._detail_now_playing.text()


class TestRefreshThemeWithMetadata:
    """Test refresh_theme with metadata."""

    def test_refresh_theme_with_title_and_album(self, qtbot: QtBot, playing_source: Source) -> None:
        """Test refresh_theme updates now playing text with album."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(playing_source)
        panel.refresh_theme()

        assert "Song Title" in panel._detail_now_playing.text()

    def test_refresh_theme_with_title_and_artist_only(self, qtbot: QtBot) -> None:
        """Test refresh_theme with title and artist but no album."""
        source = Source(
            id="s1",
            name="Test",
            status=SourceStatus.PLAYING,
            meta_title="Song",
            meta_artist="Artist",
            meta_album="",
        )
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(source)
        panel.refresh_theme()

        assert "Song" in panel._detail_now_playing.text()

    def test_refresh_theme_with_title_only(self, qtbot: QtBot) -> None:
        """Test refresh_theme with title only."""
        source = Source(
            id="s1",
            name="Test",
            status=SourceStatus.PLAYING,
            meta_title="Song",
            meta_artist="",
            meta_album="",
        )
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._update_details(source)
        panel.refresh_theme()

        assert "Song" in panel._detail_now_playing.text()


class TestShowPlaceholder:
    """Test album art placeholder."""

    def test_show_placeholder(self, qtbot: QtBot) -> None:
        """Test showing album art placeholder."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._show_album_art_placeholder()

        assert panel._original_pixmap is None
        assert "No" in panel._album_art.text()

    def test_placeholder_clears_pixmap(self, qtbot: QtBot, playing_source: Source) -> None:
        """Test placeholder clears existing pixmap."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Set a placeholder, verify it's cleared
        panel._show_album_art_placeholder()
        assert panel._original_pixmap is None


class TestPlayingSourceDisplay:
    """Test displaying playing sources in list."""

    def test_playing_source_has_indicator(self, qtbot: QtBot, playing_source: Source) -> None:
        """Test playing source shows indicator in list."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([playing_source])

        item = panel._list.item(0)
        assert "▶" in item.text()

    def test_idle_source_no_indicator(self, qtbot: QtBot, idle_source: Source) -> None:
        """Test idle source has no play indicator."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source])

        item = panel._list.item(0)
        assert "▶" not in item.text()


class TestSourceRestoreSelection:
    """Test selection restoration after set_sources."""

    def test_restore_selection(
        self, qtbot: QtBot, idle_source: Source, playing_source: Source
    ) -> None:
        """Test selection is restored after updating sources."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_sources([idle_source, playing_source])
        panel._list.setCurrentRow(1)  # Select playing_source

        # Update sources again
        panel.set_sources([idle_source, playing_source])

        # Selection should be restored
        assert panel._list.currentRow() == 1


class TestSetServerHost:
    """Test set_server_host method."""

    def test_set_server_host(self, qtbot: QtBot) -> None:
        """Test setting server host."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel.set_server_host("192.168.1.100")
        assert panel._server_host == "192.168.1.100"


class TestSetAlbumArt:
    """Test _set_album_art method."""

    def test_empty_url_no_artist_shows_placeholder(self, qtbot: QtBot) -> None:
        """Test empty URL with no artist shows placeholder."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._current_artist = None  # No artist, so no fallback triggered
        panel._art_loaded = False

        panel._set_album_art("")
        # Should show placeholder (no pixmap)
        assert panel._original_pixmap is None

    def test_unsupported_scheme_no_artist_shows_placeholder(self, qtbot: QtBot) -> None:
        """Test unsupported URL scheme with no artist shows placeholder."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._current_artist = None  # No artist, so no fallback triggered
        panel._art_loaded = False

        panel._set_album_art("ftp://example.com/art.jpg")

        # Should show placeholder (no pixmap)
        assert panel._original_pixmap is None


class TestSetPixmap:
    """Test _set_pixmap method."""

    def test_set_pixmap_stores_original(self, qtbot: QtBot) -> None:
        """Test _set_pixmap stores the original pixmap."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Create a small test pixmap
        image = QImage(100, 100, QImage.Format.Format_RGB32)
        image.fill(0xFF0000)  # Red
        pixmap = QPixmap.fromImage(image)

        panel._set_pixmap(pixmap)

        assert panel._original_pixmap is not None
        assert not panel._original_pixmap.isNull()

    def test_set_pixmap_scales_large_image(self, qtbot: QtBot) -> None:
        """Test _set_pixmap scales down large images."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Create a large test pixmap
        image = QImage(1000, 1000, QImage.Format.Format_RGB32)
        image.fill(0x00FF00)  # Green
        pixmap = QPixmap.fromImage(image)

        panel._set_pixmap(pixmap)

        # Stored pixmap should be scaled down
        assert panel._original_pixmap is not None
        assert panel._original_pixmap.width() <= panel._MAX_STORED_PIXMAP_SIZE
        assert panel._original_pixmap.height() <= panel._MAX_STORED_PIXMAP_SIZE


class TestUpdateArtHeight:
    """Test _update_art_height method."""

    def test_update_art_height_no_pixmap(self, qtbot: QtBot) -> None:
        """Test _update_art_height with no pixmap is no-op."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._original_pixmap = None
        panel._update_art_height()  # Should not crash

    def test_update_art_height_null_pixmap(self, qtbot: QtBot) -> None:
        """Test _update_art_height with null pixmap is no-op."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._original_pixmap = QPixmap()  # Null pixmap
        panel._update_art_height()  # Should not crash

    def test_update_art_height_zero_dimension(self, qtbot: QtBot) -> None:
        """Test _update_art_height with zero-dimension pixmap."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)
        panel.show()

        # Create a 1x0 pixmap (edge case)
        panel._original_pixmap = QPixmap(1, 0)
        panel._update_art_height()  # Should not crash


class TestApplyFallbackArt:
    """Test _apply_fallback_art method."""

    def test_apply_fallback_art_no_pending(self, qtbot: QtBot) -> None:
        """Test _apply_fallback_art with no pending art."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._pending_fallback_art = None
        panel._apply_fallback_art()  # Should not crash

    def test_apply_fallback_art_stale_request(self, qtbot: QtBot) -> None:
        """Test _apply_fallback_art skips stale requests."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Set up pending art with old generation
        panel._fallback_generation = 5
        panel._pending_fallback_generation = 3  # Old
        panel._pending_fallback_art = (b"test", "image/jpeg", "test")

        panel._apply_fallback_art()

        # Should have cleared pending art but not loaded
        assert panel._pending_fallback_art is None

    def test_apply_fallback_art_already_loaded(self, qtbot: QtBot) -> None:
        """Test _apply_fallback_art skips if art already loaded."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Create valid JPEG data
        image = QImage(10, 10, QImage.Format.Format_RGB32)
        image.fill(0xFF0000)

        buffer = QBuffer()
        buffer.open(QIODevice.OpenModeFlag.WriteOnly)
        image.save(buffer, "JPEG")
        jpeg_data = bytes(buffer.data())

        # Set up pending art with matching generation but art already loaded
        panel._fallback_generation = 1
        panel._pending_fallback_generation = 1
        panel._pending_fallback_art = (jpeg_data, "image/jpeg", "itunes")
        panel._art_loaded = True  # Already loaded

        panel._apply_fallback_art()

        # Should have cleared pending art but not set pixmap
        assert panel._pending_fallback_art is None


class TestApplyDataUriArt:
    """Test _apply_data_uri_art method."""

    def test_apply_data_uri_art_no_pending(self, qtbot: QtBot) -> None:
        """Test _apply_data_uri_art with no pending art."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._pending_fallback_art = None
        panel._apply_data_uri_art()  # Should not crash

    def test_apply_data_uri_art_stale_request(self, qtbot: QtBot) -> None:
        """Test _apply_data_uri_art skips stale requests."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Set up pending art with old generation
        panel._fallback_generation = 10
        panel._pending_fallback_generation = 5  # Old
        panel._pending_fallback_art = (b"test", "image/jpeg", "data-uri")

        panel._apply_data_uri_art()

        # Should have cleared pending art
        assert panel._pending_fallback_art is None


class TestLoadDataUriImage:
    """Test _load_data_uri_image method."""

    def test_invalid_data_uri_format(self, qtbot: QtBot) -> None:
        """Test _load_data_uri_image with invalid format."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # No comma separator
        result = panel._load_data_uri_image("data:image/jpeg;base64novalid")

        assert result is False

    def test_data_uri_too_large(self, qtbot: QtBot) -> None:
        """Test _load_data_uri_image rejects oversized data."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Create data URI larger than limit
        large_data = "A" * (MAX_ALBUM_ART_B64_SIZE + 1000)
        data_uri = f"data:image/jpeg;base64,{large_data}"

        result = panel._load_data_uri_image(data_uri)

        assert result is False

    def test_valid_data_uri_starts_decode(self, qtbot: QtBot) -> None:
        """Test _load_data_uri_image starts async decode for valid data."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Create a small valid data URI
        small_data = base64.b64encode(b"test").decode()
        data_uri = f"data:image/jpeg;base64,{small_data}"

        initial_gen = panel._fallback_generation

        # Mock threading to prevent background thread from emitting signals
        # during pytest-qt event cleanup (causes SIGSEGV on Linux/Python 3.14)
        with patch("snapctrl.ui.panels.sources.threading.Thread") as mock_thread:
            mock_thread.return_value = MagicMock()
            result = panel._load_data_uri_image(data_uri)

        assert result is True
        # Generation should have been incremented
        assert panel._fallback_generation > initial_gen


class TestTryFallbackArt:
    """Test _try_fallback_art method."""

    def test_try_fallback_no_artist(self, qtbot: QtBot) -> None:
        """Test _try_fallback_art with no artist shows placeholder."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._current_artist = None
        panel._art_loaded = False

        panel._try_fallback_art()

        # Should show placeholder
        assert panel._original_pixmap is None
        # art_loaded should be set to False when showing placeholder
        assert panel._art_loaded is False

    def test_try_fallback_art_already_loaded(self, qtbot: QtBot) -> None:
        """Test _try_fallback_art skips if art already loaded."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Set up state where art is already loaded
        panel._current_artist = "Test Artist"
        panel._art_loaded = True
        initial_gen = panel._fallback_generation

        panel._try_fallback_art()

        # Should not have started fallback (generation unchanged)
        assert panel._fallback_generation == initial_gen


class TestFetchHttpArt:
    """Test _fetch_http_art method."""

    def test_fetch_http_art_skip_duplicate(self, qtbot: QtBot) -> None:
        """Test _fetch_http_art skips if already fetching same URL."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        url = "http://example.com/art.jpg"
        panel._pending_art_url = url

        # Try to fetch same URL again
        panel._fetch_http_art(url)

        # Should still be the same pending URL (no new request)
        assert panel._pending_art_url == url

    def test_fetch_http_art_rewrite_local_url(self, qtbot: QtBot) -> None:
        """Test _fetch_http_art rewrites local URLs."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        panel._server_host = "192.168.1.100"
        panel._pending_art_url = ""

        # Mock the network manager to prevent actual network calls
        mock_manager = MagicMock()
        with patch.object(panel, "_network_manager", mock_manager):
            panel._fetch_http_art("http://localhost:1780/art.jpg")

        # Pending URL should be rewritten
        assert "192.168.1.100" in panel._pending_art_url
        # Verify network call was made with mocked manager
        mock_manager.get.assert_called_once()


class TestResizeEvent:
    """Test resize event handling."""

    def test_resize_event_triggers_timer(self, qtbot: QtBot) -> None:
        """Test resize event starts/restarts the debounce timer."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)
        panel.show()

        # Create resize event
        resize_event = QEvent(QEvent.Type.Resize)

        # Stop timer if already running
        panel._resize_timer.stop()
        assert not panel._resize_timer.isActive()

        # Send resize event
        panel.event(resize_event)

        # Timer should be active after resize
        assert panel._resize_timer.isActive()


class TestOnHttpArtFinished:
    """Test _on_http_art_finished handler."""

    def test_on_http_art_finished_wrong_url(self, qtbot: QtBot) -> None:
        """Test _on_http_art_finished ignores responses for old requests."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        # Set pending URL to something different
        panel._pending_art_url = "http://example.com/different.jpg"

        # Create mock reply for a different URL
        mock_reply = Mock()
        mock_reply.url.return_value.toString.return_value = "http://example.com/old.jpg"
        mock_reply.readAll.return_value.data.return_value = b"test"
        mock_reply.error.return_value = 0
        mock_reply.deleteLater = Mock()

        panel._on_http_art_finished(mock_reply)

        # Should not have changed pending URL (request ignored)
        assert panel._pending_art_url == "http://example.com/different.jpg"
