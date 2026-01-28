"""Tests for MPD client."""

import asyncio
from unittest.mock import patch

import pytest

from snapcast_mvp.api.mpd import MpdClient, MpdConnectionError


class MockStreamReader:
    """Mock asyncio StreamReader for testing."""

    def __init__(self, responses: list[bytes]) -> None:
        self._responses = responses
        self._index = 0
        self._buffer = b""

    async def readline(self) -> bytes:
        """Read a line from mock data."""
        while b"\n" not in self._buffer:
            if self._index >= len(self._responses):
                return b""
            self._buffer += self._responses[self._index]
            self._index += 1

        line, self._buffer = self._buffer.split(b"\n", 1)
        return line + b"\n"

    async def readexactly(self, n: int) -> bytes:
        """Read exactly n bytes."""
        while len(self._buffer) < n:
            if self._index >= len(self._responses):
                raise asyncio.IncompleteReadError(self._buffer, n)
            self._buffer += self._responses[self._index]
            self._index += 1

        data = self._buffer[:n]
        self._buffer = self._buffer[n:]
        return data


class MockStreamWriter:
    """Mock asyncio StreamWriter for testing."""

    def __init__(self) -> None:
        self.data: list[bytes] = []
        self._closed = False

    def write(self, data: bytes) -> None:
        """Record written data."""
        self.data.append(data)

    async def drain(self) -> None:
        """Mock drain."""
        pass

    def close(self) -> None:
        """Mark as closed."""
        self._closed = True

    async def wait_closed(self) -> None:
        """Mock wait_closed."""
        pass

    def is_closing(self) -> bool:
        """Check if closing."""
        return self._closed


@pytest.fixture
def mock_connection():
    """Create mock connection for testing."""

    def _mock_connection(responses: list[bytes]):
        reader = MockStreamReader(responses)
        writer = MockStreamWriter()
        return reader, writer

    return _mock_connection


class TestMpdClientConnection:
    """Tests for MpdClient connection handling."""

    @pytest.mark.asyncio
    async def test_connect_success(self, mock_connection) -> None:
        """Test successful connection."""
        reader, writer = mock_connection([b"OK MPD 0.23.5\n"])

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            client = MpdClient("localhost")
            await client.connect()

            assert client.is_connected
            assert client.version == "0.23.5"

            await client.disconnect()
            assert not client.is_connected

    @pytest.mark.asyncio
    async def test_connect_timeout(self) -> None:
        """Test connection timeout."""
        with patch("asyncio.open_connection", side_effect=TimeoutError()):
            client = MpdClient("localhost")
            with pytest.raises(MpdConnectionError) as excinfo:
                await client.connect()
            assert "timed out" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_connect_refused(self) -> None:
        """Test connection refused."""
        with patch(
            "asyncio.open_connection",
            side_effect=OSError("Connection refused"),
        ):
            client = MpdClient("localhost")
            with pytest.raises(MpdConnectionError) as excinfo:
                await client.connect()
            assert "Connection refused" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_connect_invalid_greeting(self, mock_connection) -> None:
        """Test invalid greeting."""
        reader, writer = mock_connection([b"INVALID\n"])

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            client = MpdClient("localhost")
            with pytest.raises(MpdConnectionError) as excinfo:
                await client.connect()
            assert "Invalid MPD greeting" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_connection) -> None:
        """Test async context manager."""
        reader, writer = mock_connection([b"OK MPD 0.23.5\n"])

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                assert client.is_connected
            # After context, should be disconnected
            assert not client.is_connected


class TestMpdClientCommands:
    """Tests for MpdClient commands."""

    @pytest.mark.asyncio
    async def test_status(self, mock_connection) -> None:
        """Test status command."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"volume: 75\nstate: play\nelapsed: 45.5\nduration: 180.0\nOK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                status = await client.status()

                assert status.volume == 75
                assert status.state == "play"
                assert status.elapsed == 45.5
                assert status.is_playing

    @pytest.mark.asyncio
    async def test_currentsong(self, mock_connection) -> None:
        """Test currentsong command."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"file: music/test.mp3\nTitle: Test Song\nArtist: Test Artist\n"
            b"Album: Test Album\nDuration: 180.5\nOK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                track = await client.currentsong()

                assert track is not None
                assert track.file == "music/test.mp3"
                assert track.title == "Test Song"
                assert track.artist == "Test Artist"
                assert track.album == "Test Album"

    @pytest.mark.asyncio
    async def test_currentsong_empty(self, mock_connection) -> None:
        """Test currentsong when stopped."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                track = await client.currentsong()
                assert track is None

    @pytest.mark.asyncio
    async def test_ping(self, mock_connection) -> None:
        """Test ping command."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                # Should not raise
                await client.ping()


class TestMpdClientAlbumArt:
    """Tests for album art commands."""

    @pytest.mark.asyncio
    async def test_albumart_success(self, mock_connection) -> None:
        """Test successful albumart retrieval."""
        # Create fake image data
        image_data = b"\xff\xd8\xff\xe0" + b"\x00" * 100
        responses = [
            b"OK MPD 0.23.5\n",
            f"size: {len(image_data)}\nbinary: {len(image_data)}\n".encode()
            + image_data
            + b"\nOK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                art = await client.albumart("music/test.mp3")

                assert art is not None
                assert art.is_valid
                assert art.uri == "music/test.mp3"
                assert len(art.data) == len(image_data)

    @pytest.mark.asyncio
    async def test_albumart_not_found(self, mock_connection) -> None:
        """Test albumart when no art exists."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"ACK [50@0] {albumart} No file exists\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                art = await client.albumart("music/test.mp3")
                assert art is None

    @pytest.mark.asyncio
    async def test_get_album_art_fallback(self, mock_connection) -> None:
        """Test get_album_art tries readpicture then albumart."""
        # readpicture fails, albumart succeeds
        image_data = b"\x89PNG" + b"\x00" * 100
        responses = [
            b"OK MPD 0.23.5\n",
            # readpicture fails
            b"ACK [50@0] {readpicture} No file exists\n",
            # albumart succeeds
            f"size: {len(image_data)}\nbinary: {len(image_data)}\n".encode()
            + image_data
            + b"\nOK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                art = await client.get_album_art("music/test.mp3")

                assert art is not None
                assert art.is_valid


class TestMpdClientPlayback:
    """Tests for playback control commands."""

    @pytest.mark.asyncio
    async def test_play(self, mock_connection) -> None:
        """Test play command."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.play()
                assert b"play\n" in writer.data

    @pytest.mark.asyncio
    async def test_play_position(self, mock_connection) -> None:
        """Test play with position."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.play(5)
                assert b"play 5\n" in writer.data

    @pytest.mark.asyncio
    async def test_pause(self, mock_connection) -> None:
        """Test pause toggle."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.pause()
                assert b"pause\n" in writer.data

    @pytest.mark.asyncio
    async def test_pause_explicit(self, mock_connection) -> None:
        """Test explicit pause state."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.pause(True)
                assert b"pause 1\n" in writer.data

                await client.pause(False)
                assert b"pause 0\n" in writer.data

    @pytest.mark.asyncio
    async def test_next_previous(self, mock_connection) -> None:
        """Test next/previous commands."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.next()
                assert b"next\n" in writer.data

                await client.previous()
                assert b"previous\n" in writer.data

    @pytest.mark.asyncio
    async def test_setvol(self, mock_connection) -> None:
        """Test volume control."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.setvol(75)
                assert b"setvol 75\n" in writer.data

    @pytest.mark.asyncio
    async def test_setvol_clamp(self, mock_connection) -> None:
        """Test volume clamping."""
        responses = [
            b"OK MPD 0.23.5\n",
            b"OK\n",
            b"OK\n",
        ]
        reader, writer = mock_connection(responses)

        with patch("asyncio.open_connection", return_value=(reader, writer)):
            async with MpdClient("localhost") as client:
                await client.setvol(150)  # Over 100
                assert b"setvol 100\n" in writer.data

                await client.setvol(-10)  # Negative
                assert b"setvol 0\n" in writer.data
