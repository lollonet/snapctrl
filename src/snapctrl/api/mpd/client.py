"""Async MPD client.

This module provides an asyncio-based MPD client following the same patterns
as SnapcastClient. It's designed for future expansion into a full MPD controller.

Example:
    async with MpdClient("192.168.1.100") as client:
        status = await client.status()
        if status.is_playing:
            track = await client.currentsong()
            print(f"Playing: {track.title} by {track.artist}")
"""

import asyncio
import logging
from typing import Self

from snapctrl.api.mpd.protocol import (
    MpdError,
    format_command,
    parse_binary_response,
    parse_response,
    parse_status,
    parse_track,
)
from snapctrl.api.mpd.types import MpdAlbumArt, MpdStatus, MpdTrack

logger = logging.getLogger(__name__)

DEFAULT_PORT = 6600
CONNECT_TIMEOUT = 5.0
COMMAND_TIMEOUT = 10.0
BINARY_CHUNK_SIZE = 8192

# MPD error codes
MPD_ERROR_NO_EXIST = 50  # No file/art exists


class MpdConnectionError(Exception):
    """Failed to connect to MPD server."""


class MpdClient:
    """Async MPD client.

    Provides methods to query MPD status and metadata.
    Designed for future expansion with playback controls.

    Attributes:
        host: MPD server hostname or IP.
        port: MPD server port (default 6600).
        password: Optional password for authentication.
    """

    def __init__(
        self,
        host: str,
        port: int = DEFAULT_PORT,
        password: str = "",
    ) -> None:
        """Initialize MPD client.

        Args:
            host: MPD server hostname or IP.
            port: MPD server port.
            password: Optional password for authentication.
        """
        self.host = host
        self.port = port
        self.password = password

        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()
        self._version: str = ""

    @property
    def is_connected(self) -> bool:
        """Return True if connected to MPD."""
        return self._writer is not None and not self._writer.is_closing()

    @property
    def version(self) -> str:
        """Return MPD protocol version from initial handshake."""
        return self._version

    async def connect(self) -> None:
        """Connect to MPD server.

        Raises:
            MpdConnectionError: If connection fails.
            MpdError: If authentication fails.
        """
        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=CONNECT_TIMEOUT,
            )

            # Read greeting: "OK MPD version"
            greeting = await self._read_line()
            if not greeting.startswith("OK MPD "):
                raise MpdConnectionError(f"Invalid MPD greeting: {greeting}")

            self._version = greeting[7:]  # Extract version after "OK MPD "
            logger.info("Connected to MPD %s at %s:%d", self._version, self.host, self.port)

            # Authenticate if password provided
            if self.password:
                await self._command("password", self.password)

        except TimeoutError as e:
            raise MpdConnectionError(f"Connection to {self.host}:{self.port} timed out") from e
        except OSError as e:
            raise MpdConnectionError(f"Failed to connect to {self.host}:{self.port}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from MPD server."""
        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except (OSError, TimeoutError, asyncio.CancelledError) as e:
                logger.debug("Expected error during MPD disconnect: %s", e)
            except Exception as e:  # noqa: BLE001
                logger.warning("Unexpected error during MPD disconnect: %s", e)
            finally:
                self._writer = None
                self._reader = None
                logger.info("Disconnected from MPD")

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *_: object) -> None:
        """Async context manager exit."""
        await self.disconnect()

    async def _read_line(self) -> str:
        """Read a single line from MPD."""
        if not self._reader:
            raise MpdConnectionError("Not connected")
        line = await self._reader.readline()
        return line.decode("utf-8").rstrip("\n")

    async def _read_until_ok(self) -> list[str]:
        """Read response lines until OK or ACK.

        Returns:
            List of response lines (including final OK/ACK).

        Raises:
            MpdError: If response is an error.
        """
        lines: list[str] = []
        while True:
            line = await self._read_line()
            lines.append(line)
            if line == "OK" or line.startswith("ACK "):
                break
        return lines

    async def _command(self, cmd: str, *args: str) -> list[str]:
        """Send command and read response.

        Args:
            cmd: Command name.
            *args: Command arguments.

        Returns:
            List of response lines (without OK).

        Raises:
            MpdConnectionError: If not connected.
            MpdError: If command returns an error.
        """
        async with self._lock:
            if not self._writer:
                raise MpdConnectionError("Not connected")

            command_str = format_command(cmd, *args)
            logger.debug("MPD command: %s", command_str)

            self._writer.write(f"{command_str}\n".encode())
            await self._writer.drain()

            lines = await asyncio.wait_for(
                self._read_until_ok(),
                timeout=COMMAND_TIMEOUT,
            )

            # parse_response will raise MpdError if ACK
            # We call it here to check for errors, then return raw lines
            parse_response(lines)

            # Return lines without the final OK
            return [line for line in lines if line != "OK"]

    async def _binary_command(self, cmd: str, *args: str) -> tuple[list[str], bytes]:
        """Send command that returns binary data.

        Binary response format:
            size: <bytes>
            type: <mime_type>  (optional, for readpicture)
            binary: <size>
            <binary data>
            OK

        Args:
            cmd: Command name.
            *args: Command arguments.

        Returns:
            Tuple of (header lines, binary data).

        Raises:
            MpdConnectionError: If not connected.
            MpdError: If command returns an error or no binary data.
        """
        async with self._lock:
            if not self._writer or not self._reader:
                raise MpdConnectionError("Not connected")

            command_str = format_command(cmd, *args)
            logger.debug("MPD binary command: %s", command_str)

            self._writer.write(f"{command_str}\n".encode())
            await self._writer.drain()

            # Read header lines until we see "binary: <size>"
            header_lines: list[str] = []
            binary_size = 0

            while True:
                line = await self._read_line()

                # Check for error
                if line.startswith("ACK "):
                    parse_response([line])  # Will raise MpdError

                # Check for OK (no binary data)
                if line == "OK":
                    return header_lines, b""

                # Check for binary header
                if line.startswith("binary: "):
                    binary_size = int(line[8:])
                    break

                header_lines.append(line)

            # Read binary data
            binary_data = await self._reader.readexactly(binary_size)

            # Read trailing newline and OK
            await self._reader.readline()  # Empty line after binary
            ok_line = await self._read_line()
            if ok_line != "OK":
                logger.warning("Expected OK after binary, got: %s", ok_line)

            return header_lines, binary_data

    # -------------------------------------------------------------------------
    # Status & Info Commands
    # -------------------------------------------------------------------------

    async def status(self) -> MpdStatus:
        """Get current player status.

        Returns:
            MpdStatus with current state, volume, etc.
        """
        lines = await self._command("status")
        data = parse_response(lines)
        return parse_status(data)

    async def currentsong(self) -> MpdTrack | None:
        """Get current song information.

        Returns:
            MpdTrack if a song is loaded, None otherwise.
        """
        lines = await self._command("currentsong")
        if not lines:
            return None
        data = parse_response(lines)
        if "file" not in data:
            return None
        return parse_track(data)

    async def stats(self) -> dict[str, str]:
        """Get database statistics.

        Returns:
            Dictionary with stats (artists, albums, songs, uptime, etc.).
        """
        lines = await self._command("stats")
        return parse_response(lines)

    # -------------------------------------------------------------------------
    # Album Art Commands
    # -------------------------------------------------------------------------

    async def albumart(self, uri: str, offset: int = 0) -> MpdAlbumArt | None:
        """Get album art from a folder (cover.jpg, etc.).

        Args:
            uri: The file URI to get art for.
            offset: Byte offset for chunked retrieval.

        Returns:
            MpdAlbumArt if available, None if no art found.
        """
        try:
            header_lines, data = await self._binary_command("albumart", uri, str(offset))
            if not data:
                return None
            return parse_binary_response(header_lines, data, uri)
        except MpdError as e:
            # Error code 50 = no album art
            if e.code == MPD_ERROR_NO_EXIST:
                return None
            raise

    async def readpicture(self, uri: str, offset: int = 0) -> MpdAlbumArt | None:
        """Get embedded album art from file tags.

        Args:
            uri: The file URI to get art for.
            offset: Byte offset for chunked retrieval.

        Returns:
            MpdAlbumArt if available, None if no embedded art.
        """
        try:
            header_lines, data = await self._binary_command("readpicture", uri, str(offset))
            if not data:
                return None
            return parse_binary_response(header_lines, data, uri)
        except MpdError as e:
            # Error code 50 = no picture
            if e.code == MPD_ERROR_NO_EXIST:
                return None
            raise

    async def _fetch_full_art(
        self,
        fetch_func: str,
        uri: str,
    ) -> MpdAlbumArt | None:
        """Fetch complete album art, handling chunked responses.

        MPD returns album art in chunks (default 8KB). This method
        fetches all chunks and concatenates them.

        Args:
            fetch_func: Command name ("readpicture" or "albumart").
            uri: The file URI to get art for.

        Returns:
            Complete MpdAlbumArt if available, None otherwise.
        """
        # Fetch first chunk to get total size
        try:
            header_lines, data = await self._binary_command(fetch_func, uri, "0")
            if not data:
                return None
        except MpdError as e:
            if e.code == MPD_ERROR_NO_EXIST:
                return None
            raise

        # Parse header for total size and mime type
        art = parse_binary_response(header_lines, data, uri)
        if not art or not art.is_valid:
            return None

        # If we have all the data, return it
        if art.size <= len(art.data):
            return art

        # Need to fetch more chunks
        all_data = bytearray(art.data)
        offset = len(art.data)

        while offset < art.size:
            try:
                _, chunk = await self._binary_command(fetch_func, uri, str(offset))
                if not chunk:
                    break
                all_data.extend(chunk)
                offset += len(chunk)
            except MpdError:
                break

        # Return complete art with all data
        return MpdAlbumArt(
            uri=art.uri,
            data=bytes(all_data),
            mime_type=art.mime_type,
            size=art.size,
        )

    async def get_album_art(self, uri: str) -> MpdAlbumArt | None:
        """Get album art, trying readpicture first, then albumart.

        This is the recommended method to get album art as it tries
        embedded art first (more reliable) then folder art.

        Handles chunked responses - MPD returns art in 8KB chunks.

        Args:
            uri: The file URI to get art for.

        Returns:
            MpdAlbumArt if available from either source, None otherwise.
        """
        # Try embedded art first (more reliable)
        art = await self._fetch_full_art("readpicture", uri)
        if art and art.is_valid:
            return art

        # Fall back to folder art
        art = await self._fetch_full_art("albumart", uri)
        if art and art.is_valid:
            return art

        return None

    # -------------------------------------------------------------------------
    # Playback Control (for future expansion)
    # -------------------------------------------------------------------------

    async def play(self, pos: int = -1) -> None:
        """Start playback.

        Args:
            pos: Position in playlist to start from, or -1 for current.
        """
        if pos >= 0:
            await self._command("play", str(pos))
        else:
            await self._command("play")

    async def pause(self, state: bool | None = None) -> None:
        """Pause or resume playback.

        Args:
            state: True to pause, False to resume, None to toggle.
        """
        if state is None:
            await self._command("pause")
        else:
            await self._command("pause", "1" if state else "0")

    async def stop(self) -> None:
        """Stop playback."""
        await self._command("stop")

    async def next(self) -> None:
        """Skip to next track."""
        await self._command("next")

    async def previous(self) -> None:
        """Skip to previous track."""
        await self._command("previous")

    async def seek(self, time: float) -> None:
        """Seek to position in current track.

        Args:
            time: Position in seconds.
        """
        await self._command("seekcur", str(time))

    async def setvol(self, volume: int) -> None:
        """Set volume.

        Args:
            volume: Volume level (0-100).
        """
        await self._command("setvol", str(max(0, min(100, volume))))

    # -------------------------------------------------------------------------
    # Utility Commands
    # -------------------------------------------------------------------------

    async def ping(self) -> None:
        """Ping MPD server to check connection."""
        await self._command("ping")

    async def idle(self, *subsystems: str) -> list[str]:
        """Wait for changes in specified subsystems.

        This is a blocking command that waits until something changes.

        Args:
            *subsystems: Subsystems to watch (player, mixer, options, etc.).
                         If empty, watches all subsystems.

        Returns:
            List of changed subsystems.
        """
        if subsystems:
            lines = await self._command("idle", *subsystems)
        else:
            lines = await self._command("idle")

        changed: list[str] = []
        for line in lines:
            if line.startswith("changed: "):
                changed.append(line[9:])
        return changed
