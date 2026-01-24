"""Tests for ServerState model."""

import pytest

from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.server import Server
from snapcast_mvp.models.server_state import ServerState
from snapcast_mvp.models.source import Source


class TestServerState:
    """Tests for ServerState dataclass."""

    def test_server_state_creation_with_defaults(self) -> None:
        """Test creating server state with default values."""
        server = Server(name="Test", host="192.168.1.1")
        state = ServerState(server=server)

        assert state.server == server
        assert state.groups == []
        assert state.clients == []
        assert state.sources == []
        assert state.connected is False
        assert state.version == ""
        assert state.host == ""
        assert state.mac == ""

    def test_server_state_with_all_params(self) -> None:
        """Test creating server state with all parameters."""
        server = Server(name="Test", host="192.168.1.1")
        client1 = Client(id="c1", host="192.168.1.10")
        client2 = Client(id="c2", host="192.168.1.11")
        group = Group(id="g1", name="Group 1", client_ids=["c1", "c2"])
        source = Source(id="s1", name="Spotify")

        state = ServerState(
            server=server,
            groups=[group],
            clients=[client1, client2],
            sources=[source],
            connected=True,
            version="0.27.0",
            host="snapcast.local",
            mac="AA:BB:CC:DD:EE:FF",
        )

        assert len(state.groups) == 1
        assert len(state.clients) == 2
        assert len(state.sources) == 1
        assert state.connected is True
        assert state.version == "0.27.0"
        assert state.host == "snapcast.local"
        assert state.mac == "AA:BB:CC:DD:EE:FF"

    def test_group_count(self) -> None:
        """Test group_count property."""
        server = Server(name="Test", host="192.168.1.1")
        state = ServerState(
            server=server,
            groups=[
                Group(id="g1"),
                Group(id="g2"),
                Group(id="g3"),
            ],
        )
        assert state.group_count == 3

    def test_client_count(self) -> None:
        """Test client_count property."""
        server = Server(name="Test", host="192.168.1.1")
        state = ServerState(
            server=server,
            clients=[
                Client(id="c1", host="192.168.1.10"),
                Client(id="c2", host="192.168.1.11"),
            ],
        )
        assert state.client_count == 2

    def test_source_count(self) -> None:
        """Test source_count property."""
        server = Server(name="Test", host="192.168.1.1")
        state = ServerState(
            server=server,
            sources=[
                Source(id="s1"),
                Source(id="s2"),
                Source(id="s3"),
                Source(id="s4"),
            ],
        )
        assert state.source_count == 4

    def test_is_connected_alias(self) -> None:
        """Test is_connected is an alias for connected."""
        server = Server(name="Test", host="192.168.1.1")
        state = ServerState(server=server, connected=True)
        assert state.is_connected is True

    def test_get_client_found(self) -> None:
        """Test get_client returns client when found."""
        server = Server(name="Test", host="192.168.1.1")
        client = Client(id="c1", host="192.168.1.10", name="Living Room")
        state = ServerState(server=server, clients=[client])

        result = state.get_client("c1")
        assert result is not None
        assert result.id == "c1"
        assert result.name == "Living Room"

    def test_get_client_not_found(self) -> None:
        """Test get_client returns None when not found."""
        server = Server(name="Test", host="192.168.1.1")
        client = Client(id="c1", host="192.168.1.10")
        state = ServerState(server=server, clients=[client])

        result = state.get_client("c999")
        assert result is None

    def test_get_group_found(self) -> None:
        """Test get_group returns group when found."""
        server = Server(name="Test", host="192.168.1.1")
        group = Group(id="g1", name="Downstairs")
        state = ServerState(server=server, groups=[group])

        result = state.get_group("g1")
        assert result is not None
        assert result.id == "g1"
        assert result.name == "Downstairs"

    def test_get_group_not_found(self) -> None:
        """Test get_group returns None when not found."""
        server = Server(name="Test", host="192.168.1.1")
        group = Group(id="g1")
        state = ServerState(server=server, groups=[group])

        result = state.get_group("g999")
        assert result is None

    def test_get_source_found(self) -> None:
        """Test get_source returns source when found."""
        server = Server(name="Test", host="192.168.1.1")
        source = Source(id="s1", name="Spotify")
        state = ServerState(server=server, sources=[source])

        result = state.get_source("s1")
        assert result is not None
        assert result.id == "s1"
        assert result.name == "Spotify"

    def test_get_source_not_found(self) -> None:
        """Test get_source returns None when not found."""
        server = Server(name="Test", host="192.168.1.1")
        source = Source(id="s1")
        state = ServerState(server=server, sources=[source])

        result = state.get_source("s999")
        assert result is None

    def test_server_state_is_immutable(self) -> None:
        """Test that ServerState instances are immutable (frozen)."""
        server = Server(name="Test", host="192.168.1.1")
        state = ServerState(server=server)
        with pytest.raises(Exception):  # FrozenInstanceError
            state.connected = True  # type: ignore[misc]
