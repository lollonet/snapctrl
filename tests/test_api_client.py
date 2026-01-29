"""Tests for SnapcastClient."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snapcast_mvp.api.client import (
    SnapcastClient,
    _parse_server_status,
)


class TestSnapcastClient:
    """Tests for SnapcastClient."""

    def test_client_initialization(self) -> None:
        """Test client initialization."""
        client = SnapcastClient("localhost")
        assert client.host == "localhost"
        assert client.port == 1705
        assert client.is_connected is False

    def test_client_initialization_with_port(self) -> None:
        """Test client initialization with custom port."""
        client = SnapcastClient("localhost", 1800)
        assert client.host == "localhost"
        assert client.port == 1800

    @pytest.mark.asyncio
    async def test_connect_success(self) -> None:
        """Test successful connection."""
        client = SnapcastClient("192.168.1.100", 1705)

        # Mock asyncio.open_connection
        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        async def mock_readline() -> bytes:
            # Simulate no more data
            return b""

        mock_reader.readline = mock_readline

        with patch(
            "snapcast_mvp.api.client.asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            await client.connect()
            assert client.is_connected is True
            await client.disconnect()

    @pytest.mark.asyncio
    async def test_connect_failure(self) -> None:
        """Test connection failure."""
        client = SnapcastClient("192.168.1.999", 1705)

        async def mock_connect_fail(*args: object, **kwargs: object) -> None:
            raise OSError("Connection refused")

        with (
            patch(
                "snapcast_mvp.api.client.asyncio.open_connection",
                side_effect=mock_connect_fail,
            ),
            pytest.raises(ConnectionError),
        ):
            await client.connect()

    @pytest.mark.asyncio
    async def test_disconnect_clears_pending(self) -> None:
        """Test that disconnect clears pending requests."""
        client = SnapcastClient("192.168.1.100", 1705)

        mock_reader = AsyncMock()
        mock_writer = AsyncMock()
        mock_writer.write = MagicMock()
        mock_writer.drain = AsyncMock()
        mock_writer.close = AsyncMock()
        mock_writer.wait_closed = AsyncMock()

        async def mock_readline() -> bytes:
            return b""

        mock_reader.readline = mock_readline

        with patch(
            "snapcast_mvp.api.client.asyncio.open_connection",
            return_value=(mock_reader, mock_writer),
        ):
            await client.connect()
            # Simulate a pending request
            client._pending[1] = asyncio.Future()
            await client.disconnect()
            assert len(client._pending) == 0

    @pytest.mark.asyncio
    async def test_call_not_connected(self) -> None:
        """Test calling when not connected."""
        client = SnapcastClient("localhost")
        with pytest.raises(ConnectionError, match="Not connected"):
            await client.call("Server.GetStatus")

    @pytest.mark.asyncio
    async def test_next_id_increments(self) -> None:
        """Test that request IDs increment."""
        client = SnapcastClient("localhost")
        assert client._next_id() == 1
        assert client._next_id() == 2
        assert client._next_id() == 3


class TestParseServerStatus:
    """Tests for _parse_server_status function."""

    def test_parse_full_response(self) -> None:
        """Test parsing full server status with real Snapcast format."""
        data = {
            "server": {
                "groups": [
                    {
                        "id": "group-1",
                        "name": "Default",
                        "stream_id": "stream-1",
                        "muted": False,
                        "clients": [
                            {
                                "id": "client-1",
                                "connected": True,
                                "host": {
                                    "ip": "192.168.1.10",
                                    "mac": "AA:BB:CC:DD:EE:FF",
                                    "name": "Living Room",
                                },
                                "config": {
                                    "name": "Speaker",
                                    "volume": {"percent": 75, "muted": False},
                                    "latency": 0,
                                },
                                "snapclient": {"version": "0.27.0"},
                            }
                        ],
                    }
                ],
                "server": {
                    "snapserver": {"version": "0.27.0"},
                    "host": {"name": "snapcast", "ip": "192.168.1.1"},
                },
                "streams": [
                    {
                        "id": "stream-1",
                        "status": "playing",
                        "uri": {"query": {"name": "Spotify", "codec": "flac"}},
                    }
                ],
            }
        }

        state = _parse_server_status(data)

        assert state.server.host == "192.168.1.1"  # IP when no name present
        assert state.version == "0.27.0"
        assert state.group_count == 1
        assert state.client_count == 1
        assert state.source_count == 1

    def test_parse_empty_response(self) -> None:
        """Test parsing minimal server status."""
        data = {"server": {"groups": [], "server": {}, "streams": []}}

        state = _parse_server_status(data)

        assert state.group_count == 0
        assert state.client_count == 0
        assert state.source_count == 0

    def test_parse_multiple_clients(self) -> None:
        """Test parsing group with multiple clients."""
        data = {
            "server": {
                "groups": [
                    {
                        "id": "g1",
                        "name": "Group",
                        "clients": [
                            {"id": "c1", "connected": True, "host": {"ip": "10.0.0.1"}},
                            {"id": "c2", "connected": False, "host": {"ip": "10.0.0.2"}},
                        ],
                    }
                ],
                "server": {"snapserver": {}, "host": {}},
                "streams": [],
            }
        }

        state = _parse_server_status(data)

        assert state.client_count == 2
        assert state.group_count == 1
        assert state.groups[0].client_ids == ["c1", "c2"]

    def test_parse_stream_status(self) -> None:
        """Test parsing stream with playing status."""
        data = {
            "server": {
                "groups": [],
                "server": {"snapserver": {}, "host": {}},
                "streams": [
                    {
                        "id": "stream-1",
                        "status": "playing",
                        "uri": {"query": {"name": "Music", "codec": "flac"}},
                    }
                ],
            }
        }

        state = _parse_server_status(data)

        assert state.source_count == 1
        source = state.sources[0]
        assert source.is_playing is True
        assert source.stream_type == "flac"


class TestSetClientMute:
    """Tests for set_client_mute method."""

    @pytest.mark.asyncio
    async def test_set_client_mute_sends_correct_payload(self) -> None:
        """Test that set_client_mute sends only the muted flag."""
        client = SnapcastClient("localhost")
        client._connected = True
        client._writer = MagicMock()
        client._writer.write = MagicMock()
        client._writer.drain = AsyncMock()

        # Mock call to capture the parameters
        with patch.object(client, "call", new_callable=AsyncMock) as mock_call:
            await client.set_client_mute("client-123", True)

            mock_call.assert_called_once_with(
                "Client.SetVolume",
                {"id": "client-123", "volume": {"muted": True}},
            )

    @pytest.mark.asyncio
    async def test_set_client_mute_unmute(self) -> None:
        """Test that set_client_mute can unmute."""
        client = SnapcastClient("localhost")
        client._connected = True

        with patch.object(client, "call", new_callable=AsyncMock) as mock_call:
            await client.set_client_mute("client-456", False)

            mock_call.assert_called_once_with(
                "Client.SetVolume",
                {"id": "client-456", "volume": {"muted": False}},
            )

    @pytest.mark.asyncio
    async def test_set_client_mute_propagates_errors(self) -> None:
        """Test that set_client_mute propagates errors from call."""
        client = SnapcastClient("localhost")
        client._connected = True

        err = ConnectionError("Lost connection")
        with (
            patch.object(client, "call", new_callable=AsyncMock, side_effect=err),
            pytest.raises(ConnectionError, match="Lost connection"),
        ):
            await client.set_client_mute("client-123", True)


class TestSetClientName:
    """Tests for set_client_name method."""

    @pytest.mark.asyncio
    async def test_set_client_name_sends_correct_payload(self) -> None:
        """Test that set_client_name sends Client.SetName with correct params."""
        client = SnapcastClient("localhost")
        client._connected = True

        with patch.object(client, "call", new_callable=AsyncMock) as mock_call:
            await client.set_client_name("client-123", "Living Room")

            mock_call.assert_called_once_with(
                "Client.SetName",
                {"id": "client-123", "name": "Living Room"},
            )

    @pytest.mark.asyncio
    async def test_set_client_name_propagates_errors(self) -> None:
        """Test that set_client_name propagates errors from call."""
        client = SnapcastClient("localhost")
        client._connected = True

        err = ConnectionError("Lost connection")
        with (
            patch.object(client, "call", new_callable=AsyncMock, side_effect=err),
            pytest.raises(ConnectionError, match="Lost connection"),
        ):
            await client.set_client_name("client-123", "New Name")


class TestSetGroupName:
    """Tests for set_group_name method."""

    @pytest.mark.asyncio
    async def test_set_group_name_sends_correct_payload(self) -> None:
        """Test that set_group_name sends Group.SetName with correct params."""
        client = SnapcastClient("localhost")
        client._connected = True

        with patch.object(client, "call", new_callable=AsyncMock) as mock_call:
            await client.set_group_name("group-abc", "Kitchen")

            mock_call.assert_called_once_with(
                "Group.SetName",
                {"id": "group-abc", "name": "Kitchen"},
            )

    @pytest.mark.asyncio
    async def test_set_group_name_propagates_errors(self) -> None:
        """Test that set_group_name propagates errors from call."""
        client = SnapcastClient("localhost")
        client._connected = True

        err = ConnectionError("Lost connection")
        with (
            patch.object(client, "call", new_callable=AsyncMock, side_effect=err),
            pytest.raises(ConnectionError, match="Lost connection"),
        ):
            await client.set_group_name("group-abc", "New Group")
