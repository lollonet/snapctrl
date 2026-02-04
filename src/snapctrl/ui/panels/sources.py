"""Sources panel - displays list of audio sources."""

import asyncio
import base64
import binascii
import ipaddress
import logging
import threading
from urllib.parse import urlparse, urlunparse

from PySide6.QtCore import QEvent, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from snapctrl.api.album_art import (
    FallbackAlbumArtProvider,
    ITunesAlbumArtProvider,
    MusicBrainzAlbumArtProvider,
)
from snapctrl.models.source import Source
from snapctrl.ui.theme import theme_manager
from snapctrl.ui.tokens import sizing, spacing, typography

logger = logging.getLogger(__name__)

# Album art display size — uses sizing.album_art token
ALBUM_ART_SIZE = sizing.album_art

# Maximum album art data size (10MB base64 ≈ 7.5MB decoded)
MAX_ALBUM_ART_B64_SIZE = 10 * 1024 * 1024
_ART_HEIGHT_MAX_RETRIES = 3

# Network request timeout (15 seconds)
_NETWORK_TIMEOUT_MS = 15000

# Tolerance for skipping redundant pixmap scaling (pixels)
_SCALE_TOLERANCE_PX = 5


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

    # Internal signal for thread-safe album art updates
    _art_decoded = Signal()

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
        # Protected by _fallback_lock for thread-safe access from background threads
        self._pending_fallback_art: tuple[bytes, str, str] | None = None
        self._pending_fallback_generation: int = 0
        self._fallback_lock = threading.Lock()

        # Flag to cancel fallback when valid art arrives
        self._art_loaded: bool = False

        # Connect internal signal for thread-safe art updates
        self._art_decoded.connect(self._apply_data_uri_art)

        # Debounce timer for resize-driven album art height updates
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.setInterval(50)
        self._resize_timer.timeout.connect(self._update_art_height)

        # Generation counter to cancel stale fallback requests
        self._fallback_generation: int = 0

        # Fallback album art provider chain: iTunes -> MusicBrainz
        self._art_provider = FallbackAlbumArtProvider(
            [
                ITunesAlbumArtProvider(),
                MusicBrainzAlbumArtProvider(),
            ]
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing.xs)

        # Header
        self._header = QLabel("Sources")
        self._header.setStyleSheet(f"font-weight: bold; font-size: {typography.title}pt;")
        layout.addWidget(self._header)

        # Source list
        p = theme_manager.palette
        self._list = QListWidget()
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {p.surface_dim};
                border: none;
                padding: {spacing.xs}px;
            }}
            QListWidget::item {{
                padding: {spacing.sm}px;
                border-radius: {sizing.border_radius_md}px;
            }}
            QListWidget::item:selected {{
                background-color: {p.surface_hover};
            }}
            QListWidget::item:hover {{
                background-color: {p.surface_elevated};
            }}
        """)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

        # Details section
        self._setup_details_section(layout)

    def _setup_details_section(self, parent_layout: QVBoxLayout) -> None:
        """Set up the details section with album art and metadata labels."""
        p = theme_manager.palette
        self._details_frame = QFrame()
        self._details_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {p.surface_dim};
                border-radius: {sizing.border_radius_md}px;
                padding: {spacing.sm}px;
            }}
            QLabel {{
                color: {p.text_secondary};
                font-size: {typography.small}pt;
            }}
        """)
        details_layout = QVBoxLayout(self._details_frame)
        details_layout.setContentsMargins(spacing.sm, spacing.sm, spacing.sm, spacing.sm)
        details_layout.setSpacing(spacing.xs)

        self._detail_status = QLabel()

        # Now Playing section with album art (vertical: art above text)
        self._now_playing_frame = QWidget()
        now_playing_layout = QVBoxLayout(self._now_playing_frame)
        now_playing_layout.setContentsMargins(0, 0, 0, 0)
        now_playing_layout.setSpacing(spacing.sm)

        # Album art — fills panel width, height adjusts to keep aspect ratio
        self._album_art = QLabel()
        self._album_art.setMinimumHeight(ALBUM_ART_SIZE)
        self._album_art.setScaledContents(True)
        self._album_art.setStyleSheet(f"""
            QLabel {{
                background-color: {p.background};
                border-radius: {sizing.border_radius_md}px;
            }}
        """)
        self._original_pixmap: QPixmap | None = None
        now_playing_layout.addWidget(self._album_art)

        # Text info (title, artist, album)
        self._detail_now_playing = QLabel()
        self._detail_now_playing.setWordWrap(True)
        self._detail_now_playing.setStyleSheet(f"color: {p.text}; font-size: {typography.body}pt;")
        self._detail_now_playing.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop
        )
        now_playing_layout.addWidget(self._detail_now_playing)

        # Track time label (e.g. "1:23 / 4:56")
        self._time_label = QLabel()
        self._time_label.setStyleSheet(
            f"color: {p.text_secondary}; font-size: {typography.body}pt;"
        )
        self._time_label.setVisible(False)
        now_playing_layout.addWidget(self._time_label)

        # Progress bar (thin, accent-colored)
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 1000)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(4)
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {p.surface_dim};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {p.accent};
                border-radius: 2px;
            }}
        """)
        self._progress_bar.setVisible(False)
        now_playing_layout.addWidget(self._progress_bar)

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
        self._original_pixmap = None
        p = theme_manager.palette
        self._album_art.clear()
        self._album_art.setScaledContents(False)  # Don't stretch text
        self._album_art.setFixedHeight(ALBUM_ART_SIZE)
        self._album_art.setStyleSheet(f"""
            QLabel {{
                background-color: {p.background};
                border-radius: {sizing.border_radius_md}px;
                color: {p.text_disabled};
            }}
        """)
        self._album_art.setText("No\nArt")
        self._album_art.setAlignment(Qt.AlignmentFlag.AlignCenter)

    # Max stored pixmap size (larger images scaled down to save memory)
    _MAX_STORED_PIXMAP_SIZE = 512

    def _set_pixmap(self, pixmap: QPixmap) -> None:
        """Store original pixmap and scale to fit label while preserving aspect ratio.

        Args:
            pixmap: Full-resolution pixmap to display.
        """
        logger.info("_set_pixmap: %dx%d", pixmap.width(), pixmap.height())
        # Scale down large images to save memory (UI only needs ~300px display)
        max_size = self._MAX_STORED_PIXMAP_SIZE
        if pixmap.width() > max_size or pixmap.height() > max_size:
            pixmap = pixmap.scaled(
                self._MAX_STORED_PIXMAP_SIZE,
                self._MAX_STORED_PIXMAP_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self._original_pixmap = pixmap
        # Don't use setScaledContents - it stretches without keeping aspect ratio
        self._album_art.setScaledContents(False)
        self._album_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._album_art.setStyleSheet(f"""
            QLabel {{
                border-radius: {sizing.border_radius_md}px;
            }}
        """)
        # Defer display so layout has assigned the label's width
        QTimer.singleShot(10, self._update_art_height)

    def _update_art_height(self, *, _retries: int = 0) -> None:
        """Scale pixmap to fit label width while preserving aspect ratio."""
        if self._original_pixmap is None or self._original_pixmap.isNull():
            return
        pw = self._original_pixmap.width()
        ph = self._original_pixmap.height()
        if pw == 0 or ph == 0:
            return
        w = self._album_art.width()
        if w == 0:
            if _retries < _ART_HEIGHT_MAX_RETRIES:
                QTimer.singleShot(10, lambda: self._update_art_height(_retries=_retries + 1))
            else:
                logger.warning(
                    "Failed to get album art width after %d retries", _ART_HEIGHT_MAX_RETRIES
                )
            return
        # Calculate height that preserves aspect ratio
        h = max(int(w * ph / pw), ALBUM_ART_SIZE)
        h = min(h, 4 * ALBUM_ART_SIZE)  # Cap to prevent excessive heights
        self._album_art.setFixedHeight(h)
        # Skip scaling if current pixmap already matches target size (performance optimization)
        current = self._album_art.pixmap()
        if (
            not current.isNull()
            and abs(current.width() - w) <= _SCALE_TOLERANCE_PX
            and abs(current.height() - h) <= _SCALE_TOLERANCE_PX
        ):
            return
        # Scale pixmap to fit label size while keeping aspect ratio
        scaled = self._original_pixmap.scaled(
            w,
            h,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self._album_art.setPixmap(scaled)

    def event(self, ev: QEvent) -> bool:
        """Update album art height on resize (debounced so layout is complete)."""
        if ev.type() == QEvent.Type.Resize:
            self._resize_timer.start()
        return super().event(ev)

    def _try_fallback_art(self) -> None:
        """Try to fetch album art from fallback providers (iTunes, MusicBrainz).

        Runs async fetch in background thread, updates UI when done.
        """
        if not self._current_artist:
            self._show_album_art_placeholder()
            self._art_loaded = False
            return

        # Skip if valid art already loaded (don't overwrite with fallback)
        if self._art_loaded:
            return

        # Increment generation to invalidate any pending fallback requests
        self._fallback_generation += 1
        current_generation = self._fallback_generation

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
                    # Store result with generation and schedule UI update on main thread
                    with self._fallback_lock:
                        self._pending_fallback_art = (art.data, art.mime_type, art.source)
                        self._pending_fallback_generation = current_generation
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
        # Safely read and clear pending art under lock
        with self._fallback_lock:
            if self._pending_fallback_art is None:
                return
            pending_art = self._pending_fallback_art
            pending_gen = self._pending_fallback_generation
            self._pending_fallback_art = None

        # Skip if this is a stale request (new fallback was started)
        if pending_gen != self._fallback_generation:
            logger.debug(
                "Skipping stale fallback art (gen %d != %d)",
                pending_gen,
                self._fallback_generation,
            )
            return

        # Skip if valid art already loaded (prevents race condition)
        if self._art_loaded:
            logger.debug("Skipping fallback art - valid art already loaded")
            return

        data, _mime_type, source = pending_art

        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._set_pixmap(pixmap)
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
        logger.debug("_set_album_art called with: %s", art_url[:80] if art_url else "None")
        if not art_url:
            # No URL from source, try fallback providers
            self._try_fallback_art()
            return

        # Handle data URIs
        if art_url.startswith("data:"):
            logger.debug("Loading data URI (gen=%d)", self._fallback_generation)
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

    def _is_private_ip(self, hostname: str) -> bool:
        """Check if hostname is a private/local IP address.

        Args:
            hostname: Hostname or IP address to check.

        Returns:
            True if hostname is localhost, loopback, or private IP range.
        """
        # Check localhost names
        if hostname in ("localhost", "localhost.localdomain"):
            return True

        try:
            ip = ipaddress.ip_address(hostname)
            return ip.is_private or ip.is_loopback or ip.is_link_local
        except ValueError:
            # Not an IP address - check for .local domain
            return hostname.endswith(".local")

    def _fetch_http_art(self, url: str) -> None:
        """Fetch album art from HTTP URL.

        Args:
            url: HTTP/HTTPS URL to fetch.
        """
        # Rewrite URL hostname only for local/loopback addresses
        # (e.g., http://localhost:1780/... → http://192.168.1.100:1780/...)
        # External URLs (coverartarchive.org, etc.) should not be rewritten
        if self._server_host:
            parsed = urlparse(url)
            hostname = parsed.hostname or ""
            is_local = self._is_private_ip(hostname)
            if is_local and hostname != self._server_host:
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                new_netloc = f"{self._server_host}:{port}"
                url = urlunparse(parsed._replace(netloc=new_netloc))

        # Skip if already fetching this URL
        if url == self._pending_art_url:
            return

        self._pending_art_url = url
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.KnownHeaders.UserAgentHeader, "SnapCTRL/1.0")
        # Follow redirects (coverartarchive.org returns 307 redirects)
        request.setAttribute(
            QNetworkRequest.Attribute.RedirectPolicyAttribute,
            QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy,
        )
        # Set timeout to prevent indefinite hanging
        request.setTransferTimeout(_NETWORK_TIMEOUT_MS)
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
                self._set_pixmap(pixmap)
                self._pending_art_url = ""
                # Mark art as loaded to prevent fallback overwriting
                self._art_loaded = True
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
        """Load image from data URI in background thread.

        Args:
            art_url: Data URI containing base64 image data.

        Returns:
            True if decode started (async), False if invalid format.
        """
        try:
            # Parse data URI: data:mime_type;base64,<data>
            _header, data_b64 = art_url.split(",", 1)

            # Check size limit to prevent memory exhaustion
            if len(data_b64) > MAX_ALBUM_ART_B64_SIZE:
                logger.warning("Album art too large (%d bytes), skipping", len(data_b64))
                return False

            # Increment generation to invalidate stale requests
            self._fallback_generation += 1
            current_generation = self._fallback_generation

            def decode_in_thread() -> None:
                """Decode base64 in background thread to avoid UI blocking."""
                try:
                    image_data = base64.b64decode(data_b64)
                    # Store result and signal main thread to apply
                    with self._fallback_lock:
                        self._pending_fallback_art = (image_data, "image/jpeg", "data-uri")
                        self._pending_fallback_generation = current_generation
                    # Emit signal to trigger UI update on main thread
                    self._art_decoded.emit()
                except (ValueError, binascii.Error) as e:
                    logger.debug("Invalid album art data URI format: %s", e)
                except MemoryError:
                    logger.error("Out of memory loading album art")

            # Start background thread for decode
            thread = threading.Thread(target=decode_in_thread, daemon=True)
            thread.start()
            return True

        except ValueError as e:
            logger.debug("Invalid album art data URI format: %s", e)

        return False

    def _apply_data_uri_art(self) -> None:
        """Apply decoded data URI art to UI (called on main thread)."""
        # Safely read and clear pending art under lock
        with self._fallback_lock:
            pending_art = self._pending_fallback_art
            pending_gen = self._pending_fallback_generation
            self._pending_fallback_art = None

        logger.debug(
            "_apply_data_uri_art: pending=%s, pending_gen=%d, current_gen=%d",
            pending_art is not None,
            pending_gen,
            self._fallback_generation,
        )
        if pending_art is None:
            return

        # Skip if this is a stale request
        if pending_gen != self._fallback_generation:
            logger.debug("Skipping stale art request")
            return

        data, _mime_type, _source = pending_art

        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            self._set_pixmap(pixmap)
            self._art_loaded = True
            logger.info("Loaded album art from data URI (%d bytes)", len(data))
        else:
            logger.warning("Failed to load pixmap from data URI (%d bytes)", len(data))

    def _update_details(self, source: Source) -> None:
        """Update the details panel with source info."""
        # Status with color
        p = theme_manager.palette
        status = source.status.capitalize()
        if source.is_playing:
            self._detail_status.setText(
                f"Status: <span style='color: {p.success};'>{status}</span>"
            )
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
                    f"<b style='color: {p.text};'>{source.meta_title}</b><br/>"
                    f"<span style='color: {p.text_secondary};'>{source.meta_artist}</span><br/>"
                    f"<span style='color: {p.text_disabled}; font-style: italic;'>"
                    f"{source.meta_album}</span>"
                )
            else:
                self._detail_now_playing.setText(
                    f"<b style='color: {p.text};'>{source.meta_title}</b><br/>"
                    f"<span style='color: {p.text_secondary};'>{source.meta_artist}</span>"
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

    @staticmethod
    def _format_time(seconds: float) -> str:
        """Format seconds as mm:ss or h:mm:ss."""
        total = int(seconds)
        h, remainder = divmod(total, 3600)
        m, s = divmod(remainder, 60)
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"

    def set_playback_status(self, elapsed: float, duration: float, state: str) -> None:
        """Update the track time display and progress bar.

        Args:
            elapsed: Elapsed time in seconds.
            duration: Total duration in seconds.
            state: MPD state ("play", "pause", "stop").
        """
        show = state in ("play", "pause") and duration > 0
        self._time_label.setVisible(show)
        self._progress_bar.setVisible(show)
        if show and duration > 0:
            self._time_label.setText(
                f"{self._format_time(elapsed)} / {self._format_time(duration)}"
            )
            pct = min(int(elapsed / duration * 1000), 1000)
            self._progress_bar.setValue(pct)

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

        # Restore selection and refresh details
        if selected_item:
            self._list.setCurrentItem(selected_item)
            # Force refresh details in case source data changed (e.g., art_url updated)
            if current_id:
                source = self._get_source_by_id(current_id)
                if source:
                    self._update_details(source)

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

    def refresh_theme(self) -> None:
        """Refresh styles when theme changes."""
        p = theme_manager.palette

        self._header.setStyleSheet(
            f"font-weight: bold; font-size: {typography.title}pt; color: {p.text};"
        )
        self._list.setStyleSheet(f"""
            QListWidget {{
                background-color: {p.surface_dim};
                border: none;
                padding: {spacing.xs}px;
            }}
            QListWidget::item {{
                padding: {spacing.sm}px;
                border-radius: {sizing.border_radius_md}px;
            }}
            QListWidget::item:selected {{
                background-color: {p.surface_hover};
            }}
            QListWidget::item:hover {{
                background-color: {p.surface_elevated};
            }}
        """)
        self._details_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {p.surface_dim};
                border-radius: {sizing.border_radius_md}px;
                padding: {spacing.sm}px;
            }}
            QLabel {{
                color: {p.text_secondary};
                font-size: {typography.small}pt;
            }}
        """)
        self._album_art.setStyleSheet(f"""
            QLabel {{
                background-color: {p.background};
                border-radius: {sizing.border_radius_md}px;
            }}
        """)
        self._detail_now_playing.setStyleSheet(f"color: {p.text}; font-size: {typography.body}pt;")
        self._time_label.setStyleSheet(
            f"color: {p.text_secondary}; font-size: {typography.body}pt;"
        )
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {p.surface_dim};
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {p.accent};
                border-radius: 2px;
            }}
        """)

        # Re-render now playing text with updated colors (HTML has embedded colors)
        if self._current_title:
            if self._current_album:
                self._detail_now_playing.setText(
                    f"<b style='color: {p.text};'>{self._current_title}</b><br/>"
                    f"<span style='color: {p.text_secondary};'>{self._current_artist}</span><br/>"
                    f"<span style='color: {p.text_disabled}; font-style: italic;'>"
                    f"{self._current_album}</span>"
                )
            elif self._current_artist:
                self._detail_now_playing.setText(
                    f"<b style='color: {p.text};'>{self._current_title}</b><br/>"
                    f"<span style='color: {p.text_secondary};'>{self._current_artist}</span>"
                )
            else:
                self._detail_now_playing.setText(
                    f"<b style='color: {p.text};'>{self._current_title}</b>"
                )
