"""Tests for Server model."""

import pytest

from snapctrl.models.server import Server


class TestServer:
    """Tests for Server dataclass."""

    def test_server_creation_with_defaults(self) -> None:
        """Test creating a server with default values."""
        server = Server(name="Living Room", host="192.168.1.100")
        assert server.name == "Living Room"
        assert server.host == "192.168.1.100"
        assert server.port == 1705  # Snapcast uses TCP on 1705, not WebSocket
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

    def test_server_address_property(self) -> None:
        """Test the address property returns host:port format."""
        server = Server(name="Test", host="10.0.0.50", port=1705)
        assert server.address == "10.0.0.50:1705"

    def test_server_address_with_custom_port(self) -> None:
        """Test address property with custom port."""
        server = Server(name="Test", host="localhost", port=1800)
        assert server.address == "localhost:1800"

    def test_server_is_immutable(self) -> None:
        """Test that Server instances are immutable (frozen)."""
        server = Server(name="Test", host="localhost")
        with pytest.raises(Exception):  # FrozenInstanceError
            server.name = "Changed"  # type: ignore[misc]

    def test_server_equality(self) -> None:
        """Test server equality comparison."""
        server1 = Server(name="Test", host="192.168.1.1", port=1705)
        server2 = Server(name="Test", host="192.168.1.1", port=1705)
        server3 = Server(name="Test", host="192.168.1.1", port=1706)

        assert server1 == server2
        assert server1 != server3
