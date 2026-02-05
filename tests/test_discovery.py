"""Tests for mDNS discovery module."""

from __future__ import annotations

from unittest.mock import MagicMock

from snapctrl.core.discovery import (
    CONTROL_PORT_OFFSET,
    SNAPCAST_SERVICE_TYPE,
    DiscoveredServer,
    SnapcastServiceListener,
)


class TestDiscoveredServer:
    """Test DiscoveredServer dataclass."""

    def test_creation(self) -> None:
        """Test basic server creation."""
        server = DiscoveredServer(
            name="Test Server",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        assert server.name == "Test Server"
        assert server.host == "192.168.1.100"
        assert server.port == 1705
        assert server.addresses == ["192.168.1.100"]

    def test_display_name(self) -> None:
        """Test display name removes service suffix."""
        server = DiscoveredServer(
            name="MyServer._snapcast._tcp.local.",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        # Should remove the service suffix
        assert server.display_name != ""

    def test_display_name_simple(self) -> None:
        """Test display name with simple name."""
        server = DiscoveredServer(
            name="MyServer",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        assert server.display_name == "MyServer"

    def test_display_name_empty_uses_host(self) -> None:
        """Test display name falls back to host when empty."""
        server = DiscoveredServer(
            name="",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        assert server.display_name == "192.168.1.100"

    def test_hostname_optional(self) -> None:
        """Test hostname is optional."""
        server = DiscoveredServer(
            name="Server",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        assert server.hostname == ""

    def test_hostname_provided(self) -> None:
        """Test hostname can be provided."""
        server = DiscoveredServer(
            name="Server",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
            hostname="myserver.local",
        )

        assert server.hostname == "myserver.local"


class TestSnapcastServiceListener:
    """Test SnapcastServiceListener."""

    def test_creation(self) -> None:
        """Test listener can be created."""
        listener = SnapcastServiceListener()
        assert listener.servers == []

    def test_creation_with_callbacks(self) -> None:
        """Test listener with callbacks."""
        on_found = MagicMock()
        on_removed = MagicMock()

        listener = SnapcastServiceListener(on_found=on_found, on_removed=on_removed)
        assert listener._on_found is on_found
        assert listener._on_removed is on_removed

    def test_servers_property(self) -> None:
        """Test servers property returns list."""
        listener = SnapcastServiceListener()
        assert isinstance(listener.servers, list)

    def test_add_service_no_info(self) -> None:
        """Test add_service handles missing info gracefully."""
        listener = SnapcastServiceListener()
        mock_zc = MagicMock()
        mock_zc.get_service_info.return_value = None

        listener.add_service(mock_zc, SNAPCAST_SERVICE_TYPE, "test")

        # Should not crash and not add server
        assert len(listener.servers) == 0

    def test_add_service_with_info(self) -> None:
        """Test add_service with valid service info."""
        on_found = MagicMock()
        listener = SnapcastServiceListener(on_found=on_found)

        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.addresses = [b"\xc0\xa8\x01\x64"]  # 192.168.1.100
        mock_info.port = 1704
        mock_info.server = "myserver.local."
        mock_info.properties = {b"name": b"Test Server"}
        mock_zc.get_service_info.return_value = mock_info

        listener.add_service(mock_zc, SNAPCAST_SERVICE_TYPE, "test._snapcast._tcp.local.")

        # Should have added server
        assert len(listener.servers) == 1
        server = listener.servers[0]
        assert server.host == "192.168.1.100"
        assert server.port == 1704 + CONTROL_PORT_OFFSET
        assert server.name == "Test Server"
        assert server.hostname == "myserver.local"

        # Callback should have been called
        on_found.assert_called_once()

    def test_add_service_no_addresses(self) -> None:
        """Test add_service handles empty addresses."""
        listener = SnapcastServiceListener()

        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.addresses = []
        mock_zc.get_service_info.return_value = mock_info

        listener.add_service(mock_zc, SNAPCAST_SERVICE_TYPE, "test")

        # Should not add server without addresses
        assert len(listener.servers) == 0

    def test_add_service_uses_mdns_name_fallback(self) -> None:
        """Test add_service falls back to mDNS name if no name property."""
        listener = SnapcastServiceListener()

        mock_zc = MagicMock()
        mock_info = MagicMock()
        mock_info.addresses = [b"\xc0\xa8\x01\x64"]  # 192.168.1.100
        mock_info.port = 1704
        mock_info.server = "host.local."
        mock_info.properties = {}  # No name property
        mock_zc.get_service_info.return_value = mock_info

        listener.add_service(mock_zc, SNAPCAST_SERVICE_TYPE, "mdns-name")

        assert len(listener.servers) == 1
        assert listener.servers[0].name == "mdns-name"

    def test_remove_service(self) -> None:
        """Test remove_service removes server and calls callback."""
        on_removed = MagicMock()
        listener = SnapcastServiceListener(on_removed=on_removed)

        # Add a server first
        listener._servers["test-service"] = DiscoveredServer(
            name="Test",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        mock_zc = MagicMock()
        listener.remove_service(mock_zc, SNAPCAST_SERVICE_TYPE, "test-service")

        # Server should be removed
        assert len(listener.servers) == 0
        on_removed.assert_called_once_with("test-service")

    def test_remove_service_nonexistent(self) -> None:
        """Test remove_service handles nonexistent service."""
        listener = SnapcastServiceListener()
        mock_zc = MagicMock()

        # Should not crash when removing nonexistent service
        listener.remove_service(mock_zc, SNAPCAST_SERVICE_TYPE, "nonexistent")

    def test_update_service(self) -> None:
        """Test update_service delegates to add_service."""
        listener = SnapcastServiceListener()
        mock_zc = MagicMock()
        mock_zc.get_service_info.return_value = None

        # update_service should call add_service
        listener.update_service(mock_zc, SNAPCAST_SERVICE_TYPE, "test")
        mock_zc.get_service_info.assert_called()


class TestConstants:
    """Test module constants."""

    def test_service_type(self) -> None:
        """Test service type constant."""
        assert SNAPCAST_SERVICE_TYPE == "_snapcast._tcp.local."

    def test_control_port_offset(self) -> None:
        """Test control port offset constant."""
        assert CONTROL_PORT_OFFSET == 1
