"""Extended tests for model classes."""

from __future__ import annotations

from snapctrl.models.client import Client, _format_time_ago
from snapctrl.models.source import Source, SourceStatus


class TestClientBasics:
    """Test Client basic functionality."""

    def test_creation(self) -> None:
        """Test basic client creation."""
        client = Client(id="c1", host="192.168.1.100")

        assert client.id == "c1"
        assert client.host == "192.168.1.100"

    def test_creation_with_all_fields(self) -> None:
        """Test client creation with all fields."""
        client = Client(
            id="c1",
            host="192.168.1.100",
            name="Test Client",
            mac="aa:bb:cc:dd:ee:ff",
            volume=75,
            muted=True,
            connected=False,
            latency=100,
            snapclient_version="0.28.0",
            last_seen_sec=1704067200,
            last_seen_usec=500000,
            host_os="Linux",
            host_arch="aarch64",
            host_name="raspberrypi",
        )

        assert client.name == "Test Client"
        assert client.mac == "aa:bb:cc:dd:ee:ff"
        assert client.volume == 75
        assert client.muted is True
        assert client.connected is False
        assert client.latency == 100
        assert client.snapclient_version == "0.28.0"
        assert client.host_os == "Linux"
        assert client.host_arch == "aarch64"
        assert client.host_name == "raspberrypi"


class TestClientDisplayName:
    """Test Client display name property."""

    def test_display_name_with_name(self) -> None:
        """Test display name returns name when set."""
        client = Client(id="c1", host="192.168.1.100", name="Custom Name")
        assert client.display_name == "Custom Name"

    def test_display_name_fallback_to_host(self) -> None:
        """Test display name falls back to host when name is empty."""
        client = Client(id="c1", host="192.168.1.100", name="")
        assert client.display_name == "192.168.1.100"


class TestClientAliases:
    """Test Client property aliases."""

    def test_is_muted_alias(self) -> None:
        """Test is_muted is alias for muted."""
        client_muted = Client(id="c1", host="h", muted=True)
        client_not_muted = Client(id="c2", host="h", muted=False)

        assert client_muted.is_muted is True
        assert client_not_muted.is_muted is False

    def test_is_connected_alias(self) -> None:
        """Test is_connected is alias for connected."""
        client_connected = Client(id="c1", host="h", connected=True)
        client_disconnected = Client(id="c2", host="h", connected=False)

        assert client_connected.is_connected is True
        assert client_disconnected.is_connected is False


class TestClientDisplaySystem:
    """Test Client display_system property."""

    def test_display_system_full(self) -> None:
        """Test display_system with OS and arch."""
        client = Client(id="c1", host="h", host_os="Linux", host_arch="aarch64")
        assert client.display_system == "Linux / aarch64"

    def test_display_system_os_only(self) -> None:
        """Test display_system with OS only."""
        client = Client(id="c1", host="h", host_os="Linux", host_arch="")
        assert client.display_system == "Linux"

    def test_display_system_arch_only(self) -> None:
        """Test display_system with arch only."""
        client = Client(id="c1", host="h", host_os="", host_arch="aarch64")
        assert client.display_system == "aarch64"

    def test_display_system_empty(self) -> None:
        """Test display_system with neither."""
        client = Client(id="c1", host="h", host_os="", host_arch="")
        assert client.display_system == ""


class TestClientDisplayLatency:
    """Test Client display_latency property."""

    def test_display_latency_zero(self) -> None:
        """Test display_latency with zero offset."""
        client = Client(id="c1", host="h", latency=0)
        assert client.display_latency == "0ms (no offset)"

    def test_display_latency_positive(self) -> None:
        """Test display_latency with positive offset."""
        client = Client(id="c1", host="h", latency=50)
        assert client.display_latency == "50ms"


class TestFormatTimeAgo:
    """Test _format_time_ago helper function."""

    def test_just_now(self) -> None:
        """Test time ago for very recent."""
        assert _format_time_ago(0) == "just now"
        assert _format_time_ago(1) == "just now"

    def test_seconds(self) -> None:
        """Test time ago for seconds."""
        assert _format_time_ago(5) == "5s ago"
        assert _format_time_ago(59) == "59s ago"

    def test_minutes(self) -> None:
        """Test time ago for minutes."""
        assert _format_time_ago(60) == "1m ago"
        assert _format_time_ago(3540) == "59m ago"

    def test_hours(self) -> None:
        """Test time ago for hours."""
        assert _format_time_ago(3600) == "1h ago"
        assert _format_time_ago(7200) == "2h ago"

    def test_days(self) -> None:
        """Test time ago for days."""
        assert _format_time_ago(86400) == "1d ago"
        assert _format_time_ago(172800) == "2d ago"


class TestSourceStatus:
    """Test SourceStatus enum."""

    def test_idle(self) -> None:
        """Test IDLE status."""
        assert SourceStatus.IDLE == "idle"

    def test_playing(self) -> None:
        """Test PLAYING status."""
        assert SourceStatus.PLAYING == "playing"

    def test_unknown(self) -> None:
        """Test UNKNOWN status."""
        assert SourceStatus.UNKNOWN == "unknown"

    def test_from_string_valid(self) -> None:
        """Test from_string with valid values."""
        assert SourceStatus.from_string("idle") == SourceStatus.IDLE
        assert SourceStatus.from_string("playing") == SourceStatus.PLAYING
        assert SourceStatus.from_string("IDLE") == SourceStatus.IDLE
        assert SourceStatus.from_string("PLAYING") == SourceStatus.PLAYING

    def test_from_string_invalid(self) -> None:
        """Test from_string with invalid value returns UNKNOWN."""
        assert SourceStatus.from_string("invalid") == SourceStatus.UNKNOWN
        assert SourceStatus.from_string("") == SourceStatus.UNKNOWN


class TestSourceBasics:
    """Test Source basic functionality."""

    def test_creation(self) -> None:
        """Test basic source creation."""
        source = Source(id="s1")

        assert source.id == "s1"
        assert source.name == ""
        assert source.status == SourceStatus.IDLE

    def test_creation_with_all_fields(self) -> None:
        """Test source creation with all fields."""
        source = Source(
            id="s1",
            name="Test Source",
            status=SourceStatus.PLAYING,
            stream_type="pipe",
            codec="flac",
            sample_format="48000:16:2",
            uri_scheme="pipe",
            uri_raw="pipe:///tmp/snapfifo?name=default",
            meta_title="Song Title",
            meta_artist="Artist Name",
            meta_album="Album Name",
            meta_art_url="http://example.com/art.jpg",
        )

        assert source.name == "Test Source"
        assert source.status == SourceStatus.PLAYING
        assert source.stream_type == "pipe"
        assert source.codec == "flac"
        assert source.sample_format == "48000:16:2"


class TestSourceProperties:
    """Test Source properties."""

    def test_is_playing_true(self) -> None:
        """Test is_playing returns True for playing status."""
        source = Source(id="s1", status=SourceStatus.PLAYING)
        assert source.is_playing is True

    def test_is_playing_false(self) -> None:
        """Test is_playing returns False for non-playing status."""
        source = Source(id="s1", status=SourceStatus.IDLE)
        assert source.is_playing is False

    def test_is_idle_true(self) -> None:
        """Test is_idle returns True for idle status."""
        source = Source(id="s1", status=SourceStatus.IDLE)
        assert source.is_idle is True

    def test_is_idle_false(self) -> None:
        """Test is_idle returns False for non-idle status."""
        source = Source(id="s1", status=SourceStatus.PLAYING)
        assert source.is_idle is False

    def test_type_alias(self) -> None:
        """Test type property is alias for stream_type."""
        source = Source(id="s1", stream_type="librespot")
        assert source.type == "librespot"


class TestSourceDisplayCodec:
    """Test Source display_codec property."""

    def test_display_codec_with_codec(self) -> None:
        """Test display_codec with codec set."""
        source = Source(id="s1", codec="flac", stream_type="pipe")
        assert source.display_codec == "flac"

    def test_display_codec_fallback_to_stream_type(self) -> None:
        """Test display_codec falls back to stream_type."""
        source = Source(id="s1", codec="", stream_type="pipe")
        assert source.display_codec == "pipe"

    def test_display_codec_unknown(self) -> None:
        """Test display_codec falls back to unknown."""
        source = Source(id="s1", codec="", stream_type="")
        assert source.display_codec == "unknown"


class TestSourceDisplayFormat:
    """Test Source display_format property."""

    def test_display_format_valid(self) -> None:
        """Test display_format with valid format."""
        source = Source(id="s1", sample_format="48000:16:2")
        assert source.display_format == "48kHz/16bit/stereo"

    def test_display_format_mono(self) -> None:
        """Test display_format with mono."""
        source = Source(id="s1", sample_format="44100:24:1")
        assert source.display_format == "44kHz/24bit/1ch"

    def test_display_format_empty(self) -> None:
        """Test display_format with empty format."""
        source = Source(id="s1", sample_format="")
        assert source.display_format == ""

    def test_display_format_invalid(self) -> None:
        """Test display_format with invalid format returns as-is."""
        source = Source(id="s1", sample_format="invalid")
        assert source.display_format == "invalid"


class TestSourceMetadata:
    """Test Source metadata properties."""

    def test_has_metadata_true(self) -> None:
        """Test has_metadata with title."""
        source = Source(id="s1", meta_title="Song")
        assert source.has_metadata is True

    def test_has_metadata_true_artist_only(self) -> None:
        """Test has_metadata with artist only."""
        source = Source(id="s1", meta_artist="Artist")
        assert source.has_metadata is True

    def test_has_metadata_false(self) -> None:
        """Test has_metadata with no metadata."""
        source = Source(id="s1")
        assert source.has_metadata is False

    def test_display_now_playing_full(self) -> None:
        """Test display_now_playing with title and artist."""
        source = Source(id="s1", meta_title="Song", meta_artist="Artist")
        assert source.display_now_playing == "Song — Artist"

    def test_display_now_playing_title_only(self) -> None:
        """Test display_now_playing with title only."""
        source = Source(id="s1", meta_title="Song", meta_artist="")
        assert source.display_now_playing == "Song"

    def test_display_now_playing_artist_only(self) -> None:
        """Test display_now_playing with artist only."""
        source = Source(id="s1", meta_title="", meta_artist="Artist")
        assert source.display_now_playing == "Artist"

    def test_display_now_playing_empty(self) -> None:
        """Test display_now_playing with no metadata."""
        source = Source(id="s1")
        assert source.display_now_playing == ""
