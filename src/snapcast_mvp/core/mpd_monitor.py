"""MPD metadata monitor for displaying track information.

This module provides a Qt-integrated monitor that polls MPD for
current track metadata and album art, emitting signals when changes occur.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal

from snapcast_mvp.api.mpd import MpdClient, MpdConnectionError, MpdError

if TYPE_CHECKING:
    from snapcast_mvp.api.mpd.types import MpdStatus, MpdTrack

logger = logging.getLogger(__name__)

DEFAULT_POLL_INTERVAL = 2.0  # seconds
DEFAULT_RECONNECT_DELAY = 5.0  # seconds
DEFAULT_ART_CACHE_SIZE = 10  # number of album arts to cache


class MpdMonitor(QObject):
    """Monitor MPD for track metadata changes.

    Runs an asyncio event loop in a background thread, polling MPD
    for current track information and album art.

    Example:
        monitor = MpdMonitor("192.168.1.100")
        monitor.track_changed.connect(lambda t: print(f"Now playing: {t.title}"))
        monitor.art_changed.connect(lambda uri, data: save_art(data))
        monitor.start()
    """

    # Emitted when the current track changes
    # Parameter: MpdTrack | None (None if no track)
    track_changed = Signal(object)

    # Emitted when player status changes (play/pause/stop)
    # Parameter: MpdStatus
    status_changed = Signal(object)

    # Emitted when album art is available
    # Parameters: (file_uri: str, art_data: bytes, mime_type: str)
    art_changed = Signal(str, bytes, str)

    # Emitted on connection state change
    # Parameter: bool (True = connected)
    connection_changed = Signal(bool)

    # Emitted on error
    # Parameter: str (error message)
    error_occurred = Signal(str)

    def __init__(
        self,
        host: str,
        port: int = 6600,
        password: str = "",
        poll_interval: float = DEFAULT_POLL_INTERVAL,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the MPD monitor.

        Args:
            host: MPD server hostname or IP.
            port: MPD server port.
            password: Optional password for authentication.
            poll_interval: Interval between status polls in seconds.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._host = host
        self._port = port
        self._password = password
        self._poll_interval = poll_interval

        self._running = False
        self._thread: threading.Thread | None = None

        # Track state for change detection
        self._last_track: MpdTrack | None = None
        self._last_status: MpdStatus | None = None
        self._last_art_uri: str = ""

        # Simple in-memory art cache: uri -> (data, mime_type)
        self._art_cache: dict[str, tuple[bytes, str]] = {}

    @property
    def host(self) -> str:
        """Return the MPD host."""
        return self._host

    @property
    def port(self) -> int:
        """Return the MPD port."""
        return self._port

    def set_host(self, host: str, port: int = 6600) -> None:
        """Update the MPD host.

        If running, will reconnect on next poll cycle.

        Args:
            host: New MPD hostname or IP.
            port: New MPD port.
        """
        self._host = host
        self._port = port

    def start(self) -> None:
        """Start the monitor."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._run_loop, daemon=True)
            self._thread.start()
            logger.info("MpdMonitor started for %s:%d", self._host, self._port)

    def stop(self) -> None:
        """Stop the monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None
            logger.info("MpdMonitor stopped")

    def _run_loop(self) -> None:
        """Background thread: run asyncio event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._monitor_loop())
        finally:
            loop.close()

    async def _monitor_loop(self) -> None:
        """Async monitor loop: connect and poll MPD."""
        while self._running:
            try:
                async with MpdClient(self._host, self._port, self._password) as client:
                    self.connection_changed.emit(True)
                    logger.info("Connected to MPD at %s:%d", self._host, self._port)

                    while self._running:
                        await self._poll_status(client)
                        await self._sleep_interruptible(self._poll_interval)

            except MpdConnectionError as e:
                logger.warning("MPD connection failed: %s", e)
                self.connection_changed.emit(False)
                self.error_occurred.emit(str(e))
                await self._sleep_interruptible(DEFAULT_RECONNECT_DELAY)

            except MpdError as e:
                logger.error("MPD protocol error: %s", e)
                self.error_occurred.emit(str(e))
                await self._sleep_interruptible(DEFAULT_RECONNECT_DELAY)

            except Exception as e:  # noqa: BLE001
                logger.exception("Unexpected error in MPD monitor: %s", e)
                self.error_occurred.emit(f"Unexpected error: {e}")
                await self._sleep_interruptible(DEFAULT_RECONNECT_DELAY)

    async def _sleep_interruptible(self, seconds: float) -> None:
        """Sleep in small increments to allow quick shutdown."""
        end_time = time.monotonic() + seconds
        while self._running and time.monotonic() < end_time:
            await asyncio.sleep(0.1)

    async def _poll_status(self, client: MpdClient) -> None:
        """Poll MPD for status and track changes."""
        try:
            # Get current status
            status = await client.status()
            self._emit_if_status_changed(status)

            # Get current track
            track = await client.currentsong()
            track_changed = self._emit_if_track_changed(track)

            # Fetch album art if track changed and has a file
            if track_changed and track and track.file:
                await self._fetch_album_art(client, track.file)

        except MpdError as e:
            logger.warning("Error polling MPD: %s", e)

    def _emit_if_status_changed(self, status: MpdStatus) -> bool:
        """Emit status_changed if status differs from last."""
        if self._last_status is None or status != self._last_status:
            self._last_status = status
            self.status_changed.emit(status)
            return True
        return False

    def _emit_if_track_changed(self, track: MpdTrack | None) -> bool:
        """Emit track_changed if track differs from last."""
        # Compare by file and ID to detect track change
        last = self._last_track
        if track is None and last is None:
            return False
        if track is None or last is None:
            self._last_track = track
            self.track_changed.emit(track)
            return True
        if track.file != last.file or track.id != last.id:
            self._last_track = track
            self.track_changed.emit(track)
            return True
        # Also check if metadata changed (same file, updated tags)
        if track.title != last.title or track.artist != last.artist or track.album != last.album:
            self._last_track = track
            self.track_changed.emit(track)
            return True
        return False

    async def _fetch_album_art(self, client: MpdClient, uri: str) -> None:
        """Fetch album art for the given file URI."""
        # Check cache first
        if uri in self._art_cache:
            data, mime_type = self._art_cache[uri]
            if uri != self._last_art_uri:
                self._last_art_uri = uri
                self.art_changed.emit(uri, data, mime_type)
            return

        try:
            art = await client.get_album_art(uri)
            if art and art.is_valid:
                # Cache the art
                self._cache_art(uri, art.data, art.mime_type)
                self._last_art_uri = uri
                self.art_changed.emit(uri, art.data, art.mime_type)
            elif uri != self._last_art_uri:
                # No art available, emit empty
                self._last_art_uri = uri
                self.art_changed.emit(uri, b"", "")
        except MpdError as e:
            logger.debug("Could not fetch album art for %s: %s", uri, e)

    def _cache_art(self, uri: str, data: bytes, mime_type: str) -> None:
        """Cache album art, evicting old entries if needed."""
        if len(self._art_cache) >= DEFAULT_ART_CACHE_SIZE:
            # Remove oldest entry (first key)
            oldest = next(iter(self._art_cache))
            del self._art_cache[oldest]
        self._art_cache[uri] = (data, mime_type)

    def clear_cache(self) -> None:
        """Clear the album art cache."""
        self._art_cache.clear()
        self._last_art_uri = ""
