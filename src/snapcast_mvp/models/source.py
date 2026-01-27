"""Source model for audio streams."""

from dataclasses import dataclass

# Sample format has 3 parts: rate:bits:channels (e.g., "48000:16:2")
_SAMPLE_FORMAT_PARTS = 3


@dataclass(frozen=True)
class Source:
    """An audio source/stream in the Snapcast server.

    Attributes:
        id: Unique stream identifier from server.
        name: Human-readable stream name.
        status: Stream status - typically "idle", "playing", or "unknown".
        stream_type: Type of stream (pipe, librespot, airplay, etc.).
        codec: Audio codec (flac, pcm, opus, ogg, etc.).
        sample_format: Sample format string (e.g., "48000:16:2").
        uri_scheme: URI scheme (pipe, librespot, airplay, meta, etc.).
        uri_raw: Raw URI string for debugging.
        meta_title: Current track title (if available).
        meta_artist: Current artist(s) (if available).
        meta_album: Current album (if available).
        meta_art_url: Album art URL (if available).
    """

    id: str
    name: str = ""
    status: str = "idle"
    stream_type: str = ""
    codec: str = ""
    sample_format: str = ""
    uri_scheme: str = ""
    uri_raw: str = ""
    meta_title: str = ""
    meta_artist: str = ""
    meta_album: str = ""
    meta_art_url: str = ""

    @property
    def is_playing(self) -> bool:
        """Return True if stream is currently playing."""
        return self.status == "playing"

    @property
    def is_idle(self) -> bool:
        """Return True if stream is idle."""
        return self.status == "idle"

    @property
    def type(self) -> str:
        """Alias for stream_type."""
        return self.stream_type

    @property
    def display_codec(self) -> str:
        """Return codec for display, with fallback."""
        return self.codec or self.stream_type or "unknown"

    @property
    def display_format(self) -> str:
        """Return sample format in human-readable form."""
        if not self.sample_format:
            return ""
        parts = self.sample_format.split(":")
        if len(parts) == _SAMPLE_FORMAT_PARTS:
            rate, bits, channels = parts
            ch_str = "stereo" if channels == "2" else f"{channels}ch"
            return f"{int(rate) // 1000}kHz/{bits}bit/{ch_str}"
        return self.sample_format

    @property
    def has_metadata(self) -> bool:
        """Return True if source has track metadata."""
        return bool(self.meta_title or self.meta_artist)

    @property
    def display_now_playing(self) -> str:
        """Return formatted 'Now Playing' string."""
        if not self.has_metadata:
            return ""
        parts: list[str] = []
        if self.meta_title:
            parts.append(self.meta_title)
        if self.meta_artist:
            parts.append(self.meta_artist)
        return " — ".join(parts)
