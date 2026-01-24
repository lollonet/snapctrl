"""Tests for Server model."""

import pytest

from snapcast_mvp.models.server import Server


class TestServer:
    """Tests for Server dataclass."""

    def test_server_creation_with_defaults(self) -> None:
        """Test creating a server with default values."""
        server = Server(name="Living Room", host="192.168.1.100")
        assert server.name == "Living Room"
        assert server.host == "192.168.1.100"
        assert server.port == 1704
        assert server.auto_connect is False

    def test_server_creation_with_all_params(self) -> None:
        """Test creating a server with all parameters."""
        server = Server(
            name="Basement",
            host="snapcast.local",
            port=1705,
            auto_connect=True,
        )
        assert server.name == "Basement"
        assert server.host == "snapcast.local"
        assert server.port == 1705
        assert server.auto_connect is True

    def test_server_url_property(self) -> None:
        """Test the url property returns correct WebSocket URL."""
        server = Server(name="Test", host="10.0.0.50", port=1704)
        assert server.url == "ws://10.0.0.50:1704/jsonrpc"

    def test_server_url_with_custom_port(self) -> None:
        """Test url property with custom port."""
        server = Server(name="Test", host="localhost", port=1800)
        assert server.url == "ws://localhost:1800/jsonrpc"

    def test_server_websocket_url_alias(self) -> None:
        """Test websocket_url is an alias for url."""
        server = Server(name="Test", host="192.168.1.1")
        assert server.websocket_url == server.url

    def test_server_is_immutable(self) -> None:
        """Test that Server instances are immutable (frozen)."""
        server = Server(name="Test", host="localhost")
        with pytest.raises(Exception):  # FrozenInstanceError
            server.name = "Changed"  # type: ignore[misc]

    def test_server_equality(self) -> None:
        """Test server equality comparison."""
        server1 = Server(name="Test", host="192.168.1.1", port=1704)
        server2 = Server(name="Test", host="192.168.1.1", port=1704)
        server3 = Server(name="Test", host="192.168.1.1", port=1705)

        assert server1 == server2
        assert server1 != server3
