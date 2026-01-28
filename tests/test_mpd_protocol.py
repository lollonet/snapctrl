"""Tests for MPD protocol parsing."""

import pytest

from snapcast_mvp.api.mpd.protocol import (
    MpdError,
    escape_arg,
    format_command,
    parse_binary_response,
    parse_response,
    parse_status,
    parse_track,
)
from snapcast_mvp.api.mpd.types import MpdStatus, MpdTrack


class TestParseResponse:
    """Tests for parse_response function."""

    def test_parse_simple_response(self) -> None:
        """Test parsing simple key-value response."""
        lines = ["key1: value1", "key2: value2", "OK"]
        result = parse_response(lines)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_parse_empty_response(self) -> None:
        """Test parsing empty response."""
        lines = ["OK"]
        result = parse_response(lines)
        assert result == {}

    def test_parse_response_with_colon_in_value(self) -> None:
        """Test parsing response where value contains colon."""
        lines = ["file: /path/to/file:with:colons.mp3", "OK"]
        result = parse_response(lines)
        assert result["file"] == "/path/to/file:with:colons.mp3"

    def test_parse_ack_error(self) -> None:
        """Test parsing ACK error response."""
        lines = ["ACK [50@0] {albumart} No file exists"]
        with pytest.raises(MpdError) as excinfo:
            parse_response(lines)
        assert excinfo.value.code == 50
        assert excinfo.value.command == "albumart"
        assert "No file exists" in excinfo.value.message

    def test_parse_lowercase_keys(self) -> None:
        """Test that keys are lowercased."""
        lines = ["Artist: Test Artist", "ALBUM: Test Album", "OK"]
        result = parse_response(lines)
        assert "artist" in result
        assert "album" in result


class TestParseTrack:
    """Tests for parse_track function."""

    def test_parse_full_track(self) -> None:
        """Test parsing track with all fields."""
        data = {
            "file": "/music/test.mp3",
            "title": "Test Song",
            "artist": "Test Artist",
            "album": "Test Album",
            "albumartist": "Album Artist",
            "duration": "180.5",
            "track": "3/12",
            "date": "2024",
            "genre": "Rock",
            "pos": "5",
            "id": "42",
        }
        track = parse_track(data)
        assert track.file == "/music/test.mp3"
        assert track.title == "Test Song"
        assert track.artist == "Test Artist"
        assert track.album == "Test Album"
        assert track.album_artist == "Album Artist"
        assert track.duration == 180.5
        assert track.track == "3/12"
        assert track.date == "2024"
        assert track.genre == "Rock"
        assert track.pos == 5
        assert track.id == 42

    def test_parse_minimal_track(self) -> None:
        """Test parsing track with only file."""
        data = {"file": "/music/test.mp3"}
        track = parse_track(data)
        assert track.file == "/music/test.mp3"
        assert track.title == ""
        assert track.artist == ""
        assert track.duration == 0.0

    def test_parse_empty_track(self) -> None:
        """Test parsing empty data."""
        data: dict[str, str] = {}
        track = parse_track(data)
        assert track.file == ""


class TestParseStatus:
    """Tests for parse_status function."""

    def test_parse_playing_status(self) -> None:
        """Test parsing playing status."""
        data = {
            "state": "play",
            "volume": "75",
            "repeat": "1",
            "random": "0",
            "single": "0",
            "consume": "0",
            "song": "5",
            "songid": "42",
            "elapsed": "45.3",
            "duration": "180.5",
            "bitrate": "320",
            "audio": "44100:16:2",
        }
        status = parse_status(data)
        assert status.state == "play"
        assert status.volume == 75
        assert status.repeat is True
        assert status.random is False
        assert status.song == 5
        assert status.song_id == 42
        assert status.elapsed == 45.3
        assert status.duration == 180.5
        assert status.bitrate == 320
        assert status.audio == "44100:16:2"
        assert status.is_playing

    def test_parse_stopped_status(self) -> None:
        """Test parsing stopped status."""
        data = {"state": "stop", "volume": "100"}
        status = parse_status(data)
        assert status.state == "stop"
        assert status.is_stopped
        assert not status.is_playing

    def test_parse_paused_status(self) -> None:
        """Test parsing paused status."""
        data = {"state": "pause"}
        status = parse_status(data)
        assert status.is_paused

    def test_parse_time_field(self) -> None:
        """Test parsing old-style time field (elapsed:duration)."""
        data = {"state": "play", "time": "45:180"}
        status = parse_status(data)
        assert status.elapsed == 45.0
        assert status.duration == 180.0

    def test_parse_empty_status(self) -> None:
        """Test parsing empty status data."""
        data: dict[str, str] = {}
        status = parse_status(data)
        assert status.state == "stop"
        assert status.volume == -1


class TestParseBinaryResponse:
    """Tests for parse_binary_response function."""

    def test_parse_binary_with_type(self) -> None:
        """Test parsing binary response with MIME type."""
        header_lines = ["size: 1024", "type: image/jpeg"]
        binary_data = b"\xff\xd8\xff\xe0" + b"\x00" * 1020
        result = parse_binary_response(header_lines, binary_data, "test.mp3")

        assert result.uri == "test.mp3"
        assert result.size == 1024
        assert result.mime_type == "image/jpeg"
        assert result.data == binary_data
        assert result.is_valid

    def test_parse_binary_without_type(self) -> None:
        """Test parsing binary response without MIME type."""
        header_lines = ["size: 512"]
        binary_data = b"\x00" * 512
        result = parse_binary_response(header_lines, binary_data, "test.mp3")

        assert result.mime_type == ""
        assert result.size == 512
        assert result.is_valid

    def test_parse_empty_binary(self) -> None:
        """Test parsing empty binary response."""
        header_lines: list[str] = []
        result = parse_binary_response(header_lines, b"", "test.mp3")

        assert not result.is_valid


class TestEscapeArg:
    """Tests for escape_arg function."""

    def test_simple_arg(self) -> None:
        """Test that simple args are not modified."""
        assert escape_arg("simple") == "simple"
        assert escape_arg("path/to/file") == "path/to/file"

    def test_empty_arg(self) -> None:
        """Test empty arg is quoted."""
        assert escape_arg("") == '""'

    def test_arg_with_spaces(self) -> None:
        """Test arg with spaces is quoted."""
        assert escape_arg("with spaces") == '"with spaces"'

    def test_arg_with_quotes(self) -> None:
        """Test arg with quotes is escaped."""
        assert escape_arg('say "hello"') == '"say \\"hello\\""'

    def test_arg_with_backslash(self) -> None:
        """Test arg with backslash is escaped."""
        assert escape_arg("path\\to\\file") == '"path\\\\to\\\\file"'


class TestFormatCommand:
    """Tests for format_command function."""

    def test_command_without_args(self) -> None:
        """Test command without arguments."""
        assert format_command("status") == "status"

    def test_command_with_simple_arg(self) -> None:
        """Test command with simple argument."""
        assert format_command("albumart", "test.mp3", "0") == "albumart test.mp3 0"

    def test_command_with_quoted_arg(self) -> None:
        """Test command with argument that needs quoting."""
        assert (
            format_command("albumart", "path with spaces.mp3") == 'albumart "path with spaces.mp3"'
        )


class TestMpdTrackProperties:
    """Tests for MpdTrack properties."""

    def test_has_metadata(self) -> None:
        """Test has_metadata property."""
        track = MpdTrack(file="test.mp3", title="Test")
        assert track.has_metadata

        track = MpdTrack(file="test.mp3", artist="Artist")
        assert track.has_metadata

        track = MpdTrack(file="test.mp3")
        assert not track.has_metadata

    def test_display_title(self) -> None:
        """Test display_title property."""
        track = MpdTrack(file="test.mp3", title="Test Song")
        assert track.display_title == "Test Song"

        # Fallback to filename
        track = MpdTrack(file="/path/to/file.mp3")
        assert track.display_title == "file"

    def test_display_artist(self) -> None:
        """Test display_artist property."""
        track = MpdTrack(file="test.mp3", artist="Track Artist")
        assert track.display_artist == "Track Artist"

        # Fallback to album artist
        track = MpdTrack(file="test.mp3", album_artist="Album Artist")
        assert track.display_artist == "Album Artist"

        # Empty when no artist
        track = MpdTrack(file="test.mp3")
        assert track.display_artist == ""


class TestMpdStatusProperties:
    """Tests for MpdStatus properties."""

    def test_is_playing(self) -> None:
        """Test is_playing property."""
        status = MpdStatus(state="play")
        assert status.is_playing
        assert not status.is_paused
        assert not status.is_stopped

    def test_progress(self) -> None:
        """Test progress property."""
        status = MpdStatus(state="play", elapsed=45.0, duration=180.0)
        assert status.progress == 0.25

        # No duration
        status = MpdStatus(state="stop", duration=0.0)
        assert status.progress == 0.0

        # Past duration (edge case)
        status = MpdStatus(state="play", elapsed=200.0, duration=180.0)
        assert status.progress == 1.0
