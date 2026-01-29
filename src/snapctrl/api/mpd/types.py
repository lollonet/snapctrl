"""MPD protocol data types.

This module defines frozen dataclasses for MPD responses,
following the same patterns as the Snapcast models.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class MpdTrack:
    """Current track information from MPD.

    Attributes:
        file: Path to the audio file in MPD's music directory.
        title: Track title from tags.
        artist: Artist name(s) from tags.
        album: Album name from tags.
        album_artist: Album artist (if different from track artist).
        duration: Track duration in seconds.
        track: Track number (e.g., "3" or "3/12").
        date: Release date/year.
        genre: Genre tag.
        pos: Position in the current playlist.
        id: MPD song ID in the current playlist.
    """

    file: str
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    duration: float = 0.0
    track: str = ""
    date: str = ""
    genre: str = ""
    pos: int = -1
    id: int = -1

    @property
    def has_metadata(self) -> bool:
        """Return True if track has title or artist metadata."""
        return bool(self.title or self.artist)

    @property
    def display_title(self) -> str:
        """Return title for display, with filename fallback."""
        if self.title:
            return self.title
        # Extract filename without path and extension
        name = self.file.rsplit("/", 1)[-1]
        if "." in name:
            name = name.rsplit(".", 1)[0]
        return name

    @property
    def display_artist(self) -> str:
        """Return artist for display, falling back to album_artist if empty."""
        return self.artist or self.album_artist or ""


@dataclass(frozen=True)
class MpdStatus:
    """MPD player status.

    Attributes:
        state: Player state - "play", "pause", or "stop".
        volume: Volume level (0-100), or -1 if not available.
        repeat: Repeat mode enabled.
        random: Random/shuffle mode enabled.
        single: Single mode (stop after current track).
        consume: Consume mode (remove tracks after playing).
        song: Current song position in playlist.
        song_id: Current song ID.
        elapsed: Elapsed time in seconds.
        duration: Total duration of current track in seconds.
        bitrate: Current audio bitrate in kbps.
        audio: Audio format string (e.g., "44100:16:2").
        error: Error message if any.
    """

    state: str = "stop"
    volume: int = -1
    repeat: bool = False
    random: bool = False
    single: bool = False
    consume: bool = False
    song: int = -1
    song_id: int = -1
    elapsed: float = 0.0
    duration: float = 0.0
    bitrate: int = 0
    audio: str = ""
    error: str = ""

    @property
    def is_playing(self) -> bool:
        """Return True if currently playing."""
        return self.state == "play"

    @property
    def is_paused(self) -> bool:
        """Return True if paused."""
        return self.state == "pause"

    @property
    def is_stopped(self) -> bool:
        """Return True if stopped."""
        return self.state == "stop"

    @property
    def progress(self) -> float:
        """Return playback progress as a fraction (0.0 to 1.0)."""
        if self.duration <= 0:
            return 0.0
        return min(1.0, self.elapsed / self.duration)


@dataclass(frozen=True)
class MpdAlbumArt:
    """Album art data from MPD.

    Attributes:
        uri: The file URI this art is associated with.
        data: Raw image bytes.
        mime_type: MIME type (e.g., "image/jpeg", "image/png").
        size: Total size in bytes.
    """

    uri: str
    data: bytes
    mime_type: str = ""
    size: int = 0

    @property
    def is_valid(self) -> bool:
        """Return True if art data is present."""
        return len(self.data) > 0
