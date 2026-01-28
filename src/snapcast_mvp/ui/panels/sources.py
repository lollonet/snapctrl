"""Sources panel - displays list of audio sources."""

import asyncio
import base64
import binascii
import logging
import threading
from urllib.parse import urlparse, urlunparse

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from snapcast_mvp.api.album_art import (
    FallbackAlbumArtProvider,
    ITunesAlbumArtProvider,
    MusicBrainzAlbumArtProvider,
)
from snapcast_mvp.models.source import Source

logger = logging.getLogger(__name__)

# Album art display size
ALBUM_ART_SIZE = 80

# Maximum album art data size (10MB base64 ≈ 7.5MB decoded)
MAX_ALBUM_ART_B64_SIZE = 10 * 1024 * 1024


class SourcesPanel(QWidget):
    """Left panel showing list of audio sources.

    Displays available audio sources (streams) with their playing status.
    Users can double-click to switch the currently selected group to that source.
    Shows details of the selected source below the list.

    Example:
        panel = SourcesPanel()
        panel.source_selected.connect(lambda sid: print(f"Selected: {sid}"))
        panel.set_sources([
            Source(id="1", name="MPD", status="playing", stream_type="flac"),
            Source(id="2", name="Spotify", status="idle", stream_type="ogg"),
        ])
    """

    # Signal emitted when a source is double-clicked (for switching groups)
    source_selected = Signal(str)  # source_id

    def __init__(self) -> None:
        """Initialize the sources panel."""
        super().__init__()
        self._sources: list[Source] = []

        # Network manager for fetching HTTP album art
        self._network_manager = QNetworkAccessManager(self)
        self._network_manager.finished.connect(self._on_http_art_finished)
        self._pending_art_url: str = ""  # Track pending request
        self._server_host: str = ""  # Connection host for URL rewriting

        # Current source metadata for fallback lookup
        self._current_artist: str = ""
        self._current_album: str = ""
        self._current_title: str = ""

        # Pending fallback art result (data, mime_type, source)
        self._pending_fallback_art: tuple[bytes, str, str] | None = None

        # Fallback album art provider chain: iTunes -> MusicBrainz
        self._art_provider = FallbackAlbumArtProvider(
            [
                ITunesAlbumArtProvider(),
                MusicBrainzAlbumArtProvider(),
            ]
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QLabel("Sources")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)

        # Source list
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #252525;
                border: none;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
        """)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

        # Details section
        self._setup_details_section(layout)

    def _setup_details_section(self, parent_layout: QVBoxLayout) -> None:
        """Set up the details section with album art and metadata labels."""
        self._details_frame = QFrame()
        self._details_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 4px;
                padding: 8px;
            }
            QLabel {
                color: #b0b0b0;
                font-size: 9pt;
            }
        """)
        details_layout = QVBoxLayout(self._details_frame)
        details_layout.setContentsMargins(8, 8, 8, 8)
        details_layout.setSpacing(4)

        self._detail_status = QLabel()

        # Now Playing section with album art
        self._now_playing_frame = QWidget()
        now_playing_layout = QHBoxLayout(self._now_playing_frame)
        now_playing_layout.setContentsMargins(0, 0, 0, 0)
        now_playing_layout.setSpacing(8)

        # Album art
        self._album_art = QLabel()
        self._album_art.setFixedSize(ALBUM_ART_SIZE, ALBUM_ART_SIZE)
        self._album_art.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border-radius: 4px;
            }
        """)
        self._album_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._album_art.setScaledContents(True)
        now_playing_layout.addWidget(self._album_art)

        # Text info (title, artist, album)
        self._detail_now_playing = QLabel()
        self._detail_now_playing.setWordWrap(True)
        self._detail_now_playing.setStyleSheet("color: #ffffff; font-size: 10pt;")
        self._detail_now_playing.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        now_playing_layout.addWidget(self._detail_now_playing, 1)

        self._detail_type = QLabel()
        self._detail_codec = QLabel()
        self._detail_format = QLabel()

        details_layout.addWidget(self._detail_status)
        details_layout.addWidget(self._now_playing_frame)
        details_layout.addWidget(self._detail_type)
        details_layout.addWidget(self._detail_codec)
        details_layout.addWidget(self._detail_format)

        parent_layout.addWidget(self._details_frame)
        self._details_frame.setVisible(False)  # Hidden until selection

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on a source item.

        Args:
            item: The clicked list item.
        """
        source_id = item.data(Qt.ItemDataRole.UserRole)
        if source_id:
            self.source_selected.emit(source_id)

    def _on_selection_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        """Handle selection change to update details panel."""
        if not current:
            self._details_frame.setVisible(False)
            return

        source_id = current.data(Qt.ItemDataRole.UserRole)
        source = self._get_source_by_id(source_id)
        if source:
            self._update_details(source)
            self._details_frame.setVisible(True)
        else:
            self._details_frame.setVisible(False)

    def _get_source_by_id(self, source_id: str) -> Source | None:
        """Get source by ID from cached list."""
        for source in self._sources:
            if source.id == source_id:
                return source
        return None

    def set_server_host(self, host: str) -> None:
        """Set the server host for URL rewriting.

        Album art URLs from Snapcast may use internal hostnames.
        This host is used to rewrite those URLs to be reachable.

        Args:
            host: The server host/IP used for connection.
        """
        self._server_host = host

    def _show_album_art_placeholder(self) -> None:
        """Show the 'No Art' placeholder for album art."""
        self._album_art.clear()
        self._album_art.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border-radius: 4px;
                color: #404040;
            }
        """)
        self._album_art.setText("No\nArt")
        self._album_art.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def _try_fallback_art(self) -> None:
        """Try to fetch album art from fallback providers (iTunes, MusicBrainz).

        Runs async fetch in background thread, updates UI when done.
        """
        if not self._current_artist:
            self._show_album_art_placeholder()
            return

        # Show placeholder while fetching
        self._show_album_art_placeholder()

        # Capture current metadata for the async call
        artist = self._current_artist
        album = self._current_album
        title = self._current_title

        def fetch_in_thread() -> None:
            """Run async fetch in background thread."""
            loop = asyncio.new_event_loop()
            try:
                art = loop.run_until_complete(self._art_provider.fetch(artist, album, title))
                if art and art.is_valid:
                    # Store result and schedule UI update on main thread
                    self._pending_fallback_art = (art.data, art.mime_type, art.source)
                    QTimer.singleShot(0, self._apply_fallback_art)
            except Exception as e:  # noqa: BLE001
                logger.debug("Fallback album art failed: %s", e)
            finally:
                loop.close()

        # Start background thread
        thread = threading.Thread(target=fetch_in_thread, daemon=True)
        thread.start()

    def _apply_fallback_art(self) -> None:
        """Apply fallback album art to UI (called on main thread)."""
        if self._pending_fallback_art is None:
            return

        data, _mime_type, source = self._pending_fallback_art
        self._pending_fallback_art = None

        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            scaled = pixmap.scaled(
                ALBUM_ART_SIZE,
                ALBUM_ART_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._album_art.setPixmap(scaled)
            self._album_art.setStyleSheet("""
                QLabel {
                    border-radius: 4px;
                }
            """)
            logger.info(
                "Album art from %s for %s - %s",
                source,
                self._current_artist,
                self._current_album or self._current_title,
            )

    def _set_album_art(self, art_url: str) -> None:
        """Set the album art image.

        Args:
            art_url: Album art URL (data URI or http URL).
        """
        if not art_url:
            # No URL from source, try fallback providers
            self._try_fallback_art()
            return

        # Handle data URIs
        if art_url.startswith("data:"):
            if self._load_data_uri_image(art_url):
                return
            # Data URI failed, try fallback
            self._try_fallback_art()
            return

        # Handle HTTP/HTTPS URLs
        if art_url.startswith(("http://", "https://")):
            self._fetch_http_art(art_url)
            return

        # Unknown URL scheme, try fallback
        logger.debug("Unsupported album art URL scheme: %s", art_url[:50])
        self._try_fallback_art()

    def _fetch_http_art(self, url: str) -> None:
        """Fetch album art from HTTP URL.

        Args:
            url: HTTP/HTTPS URL to fetch.
        """
        # Rewrite URL hostname if we have a server host
        if self._server_host:
            parsed = urlparse(url)
            if parsed.hostname:
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                new_netloc = f"{self._server_host}:{port}"
                url = urlunparse(parsed._replace(netloc=new_netloc))

        # Skip if already fetching this URL
        if url == self._pending_art_url:
            return

        self._pending_art_url = url
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "SnapCTRL/1.0")
        self._network_manager.get(request)
        logger.debug("Fetching album art from: %s", url)

    def _on_http_art_finished(self, reply: QNetworkReply) -> None:
        """Handle completed HTTP album art request.

        Args:
            reply: The network reply containing image data.
        """
        url = reply.url().toString()

        # Read data even if there was an error (Snapcast has buggy Content-Length)
        image_data = reply.readAll().data()
        error = reply.error()
        reply.deleteLater()

        # Only process if this is still the current request
        if url != self._pending_art_url:
            return

        # Try to load whatever data we got (Snapcast sends incomplete responses)
        if image_data:
            pixmap = QPixmap()
            if pixmap.loadFromData(image_data):
                scaled = pixmap.scaled(
                    ALBUM_ART_SIZE,
                    ALBUM_ART_SIZE,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
                self._album_art.setPixmap(scaled)
                self._album_art.setStyleSheet("""
                    QLabel {
                        border-radius: 4px;
                    }
                """)
                self._pending_art_url = ""
                logger.debug("Loaded album art from %s (%d bytes)", url, len(image_data))
                return

        # Failed to load from HTTP, try fallback providers
        if error != QNetworkReply.NetworkError.NoError:
            logger.warning("Failed to fetch album art from %s: %s", url, reply.errorString())
        else:
            logger.warning("Failed to decode album art from %s", url)
        self._pending_art_url = ""
        self._try_fallback_art()

    def _load_data_uri_image(self, art_url: str) -> bool:
        """Load image from data URI.

        Args:
            art_url: Data URI containing base64 image data.

        Returns:
            True if successfully loaded, False otherwise.
        """
        try:
            # Parse data URI: data:mime_type;base64,<data>
            _header, data_b64 = art_url.split(",", 1)

            # Check size limit to prevent memory exhaustion
            if len(data_b64) > MAX_ALBUM_ART_B64_SIZE:
                logger.warning("Album art too large (%d bytes), skipping", len(data_b64))
                return False

            image_data = base64.b64decode(data_b64)
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)

            if pixmap.isNull():
                return False

            scaled = pixmap.scaled(
                ALBUM_ART_SIZE,
                ALBUM_ART_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._album_art.setPixmap(scaled)
            self._album_art.setStyleSheet("""
                QLabel {
                    border-radius: 4px;
                }
            """)
            return True
        except (ValueError, binascii.Error) as e:
            logger.debug("Invalid album art data URI format: %s", e)
        except MemoryError:
            logger.error("Out of memory loading album art")
        except OSError as e:
            logger.warning("System error loading album art: %s", e)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Unexpected error loading album art: %s", type(e).__name__, exc_info=True
            )

        return False

    def _update_details(self, source: Source) -> None:
        """Update the details panel with source info."""
        # Status with color
        status = source.status.capitalize()
        if source.is_playing:
            self._detail_status.setText(f"Status: <span style='color: #80ff80;'>{status}</span>")
        else:
            self._detail_status.setText(f"Status: {status}")
        self._detail_status.setTextFormat(Qt.TextFormat.RichText)

        # Now Playing (track metadata with album art)
        if source.has_metadata:
            # Store metadata for fallback lookup
            self._current_artist = source.meta_artist
            self._current_album = source.meta_album
            self._current_title = source.meta_title

            # Show title on first line, artist/album on second if available
            if source.meta_album:
                self._detail_now_playing.setText(
                    f"<b>{source.meta_title}</b><br/>"
                    f"<span style='color: #b0b0b0;'>{source.meta_artist}</span><br/>"
                    f"<span style='color: #808080; font-style: italic;'>{source.meta_album}</span>"
                )
            else:
                self._detail_now_playing.setText(
                    f"<b>{source.meta_title}</b><br/>"
                    f"<span style='color: #b0b0b0;'>{source.meta_artist}</span>"
                )
            self._detail_now_playing.setTextFormat(Qt.TextFormat.RichText)

            # Update album art (will use fallback if no URL or HTTP fails)
            self._set_album_art(source.meta_art_url)

            self._now_playing_frame.setVisible(True)
        else:
            # Clear stored metadata
            self._current_artist = ""
            self._current_album = ""
            self._current_title = ""
            self._now_playing_frame.setVisible(False)

        # Type (scheme)
        scheme = source.uri_scheme or source.stream_type or "unknown"
        self._detail_type.setText(f"Type: {scheme}")

        # Codec
        codec = source.display_codec
        self._detail_codec.setText(f"Codec: {codec}")

        # Sample format
        fmt = source.display_format
        if fmt:
            self._detail_format.setText(f"Format: {fmt}")
            self._detail_format.setVisible(True)
        else:
            self._detail_format.setVisible(False)

    def set_sources(self, sources: list[Source]) -> None:
        """Update the list of sources.

        Args:
            sources: List of Source objects to display.
        """
        # Cache sources for details lookup
        self._sources = sources

        # Remember current selection
        current_id = self.get_selected_source_id()

        self._list.clear()

        selected_item = None
        for source in sources:
            # Create item with icon indicator for playing status
            status_icon = "▶ " if source.is_playing else "  "
            item = QListWidgetItem(f"{status_icon}{source.name}")
            item.setData(Qt.ItemDataRole.UserRole, source.id)

            if source.is_playing:
                item.setForeground(Qt.GlobalColor.green)

            self._list.addItem(item)

            # Track previously selected item
            if source.id == current_id:
                selected_item = item

        # Restore selection
        if selected_item:
            self._list.setCurrentItem(selected_item)

    def clear_sources(self) -> None:
        """Clear all sources from the list."""
        self._list.clear()

    def get_selected_source_id(self) -> str | None:
        """Get the ID of the currently selected source.

        Returns:
            Source ID, or None if no selection.
        """
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
