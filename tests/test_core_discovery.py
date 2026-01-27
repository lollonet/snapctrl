"""Tests for mDNS/Zeroconf discovery module."""

from unittest.mock import MagicMock, patch

import pytest

from snapcast_mvp.core.discovery import (
    CONTROL_PORT_OFFSET,
    SNAPCAST_SERVICE_TYPE,
    DiscoveredServer,
    ServerDiscovery,
    SnapcastServiceListener,
)


class TestDiscoveredServer:
    """Tests for DiscoveredServer dataclass."""

    def test_basic_creation(self) -> None:
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

    def test_display_name_simple(self) -> None:
        """Test display_name with simple name."""
        server = DiscoveredServer(
            name="My Server",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )
        assert server.display_name == "My Server"

    def test_display_name_with_service_suffix(self) -> None:
        """Test display_name strips service type suffix."""
        server = DiscoveredServer(
            name=f"Snapcast.{SNAPCAST_SERVICE_TYPE}",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )
        # Should strip the suffix
        assert "._tcp.local." not in server.display_name

    def test_display_name_empty_falls_back_to_host(self) -> None:
        """Test display_name uses host when name is empty."""
        server = DiscoveredServer(
            name="",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )
        assert server.display_name == "192.168.1.100"

    def test_multiple_addresses(self) -> None:
        """Test server with multiple addresses."""
        server = DiscoveredServer(
            name="Test",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100", "10.0.0.50"],
        )
        assert len(server.addresses) == 2


class TestSnapcastServiceListener:
    """Tests for SnapcastServiceListener."""

    def test_initialization(self) -> None:
        """Test listener initialization."""
        listener = SnapcastServiceListener()
        assert listener.servers == []

    def test_initialization_with_callbacks(self) -> None:
        """Test listener with callbacks."""
        on_found = MagicMock()
        on_removed = MagicMock()
        listener = SnapcastServiceListener(on_found=on_found, on_removed=on_removed)
        assert listener._on_found == on_found
        assert listener._on_removed == on_removed

    def test_servers_property_returns_list(self) -> None:
        """Test servers property returns a list."""
        listener = SnapcastServiceListener()
        assert isinstance(listener.servers, list)

    def test_add_service_with_no_info(self) -> None:
        """Test add_service handles missing service info gracefully."""
        listener = SnapcastServiceListener()
        mock_zc = MagicMock()
        mock_zc.get_service_info.return_value = None

        listener.add_service(mock_zc, SNAPCAST_SERVICE_TYPE, "TestService")

        assert len(listener.servers) == 0

    def test_remove_service_nonexistent(self) -> None:
        """Test remove_service handles non-existent service gracefully."""
        listener = SnapcastServiceListener()
        mock_zc = MagicMock()

        # Should not raise
        listener.remove_service(mock_zc, SNAPCAST_SERVICE_TYPE, "NonExistent")

    def test_remove_service_calls_callback(self) -> None:
        """Test remove_service calls on_removed callback."""
        on_removed = MagicMock()
        listener = SnapcastServiceListener(on_removed=on_removed)

        # Add a mock server directly
        listener._servers["TestService"] = DiscoveredServer(
            name="Test",
            host="192.168.1.100",
            port=1705,
            addresses=["192.168.1.100"],
        )

        mock_zc = MagicMock()
        listener.remove_service(mock_zc, SNAPCAST_SERVICE_TYPE, "TestService")

        on_removed.assert_called_once_with("TestService")
        assert "TestService" not in listener._servers


class TestServerDiscovery:
    """Tests for ServerDiscovery class."""

    def test_initialization(self) -> None:
        """Test discovery initialization."""
        discovery = ServerDiscovery()
        assert discovery._zeroconf is None
        assert discovery._browser is None
        assert discovery._listener is None

    def test_servers_empty_when_not_started(self) -> None:
        """Test servers returns empty list when not started."""
        discovery = ServerDiscovery()
        assert discovery.servers == []

    @patch("snapcast_mvp.core.discovery.Zeroconf")
    @patch("snapcast_mvp.core.discovery.ServiceBrowser")
    def test_start_creates_browser(
        self, mock_browser_cls: MagicMock, mock_zc_cls: MagicMock
    ) -> None:
        """Test start creates Zeroconf and ServiceBrowser."""
        discovery = ServerDiscovery()
        discovery.start()

        mock_zc_cls.assert_called_once()
        mock_browser_cls.assert_called_once()
        assert discovery._zeroconf is not None

        discovery.stop()

    @patch("snapcast_mvp.core.discovery.Zeroconf")
    @patch("snapcast_mvp.core.discovery.ServiceBrowser")
    def test_start_idempotent(
        self, mock_browser_cls: MagicMock, mock_zc_cls: MagicMock
    ) -> None:
        """Test start is idempotent (doesn't create multiple browsers)."""
        discovery = ServerDiscovery()
        discovery.start()
        discovery.start()  # Second call should be no-op

        # Should only be called once
        assert mock_zc_cls.call_count == 1

        discovery.stop()

    @patch("snapcast_mvp.core.discovery.Zeroconf")
    @patch("snapcast_mvp.core.discovery.ServiceBrowser")
    def test_stop_cleans_up(
        self, mock_browser_cls: MagicMock, mock_zc_cls: MagicMock
    ) -> None:
        """Test stop cleans up resources."""
        discovery = ServerDiscovery()
        discovery.start()
        discovery.stop()

        assert discovery._zeroconf is None
        assert discovery._browser is None
        assert discovery._listener is None


class TestConstants:
    """Tests for module constants."""

    def test_service_type_format(self) -> None:
        """Test service type has correct format."""
        assert SNAPCAST_SERVICE_TYPE == "_snapcast._tcp.local."

    def test_control_port_offset(self) -> None:
        """Test control port offset is 1."""
        assert CONTROL_PORT_OFFSET == 1
        # Streaming port 1704 + offset should give control port 1705
        assert 1704 + CONTROL_PORT_OFFSET == 1705


class TestDiscoveryIntegration:
    """Integration-style tests for discovery (mocked network)."""

    @pytest.mark.asyncio
    async def test_discover_one_timeout(self) -> None:
        """Test discover_one returns None on timeout."""
        with patch("snapcast_mvp.core.discovery.Zeroconf"), patch(
            "snapcast_mvp.core.discovery.ServiceBrowser"
        ):
            # With mocked Zeroconf, no servers will be found
            result = ServerDiscovery.discover_one(timeout=0.1)
            assert result is None

    @pytest.mark.asyncio
    async def test_discover_all_returns_list(self) -> None:
        """Test discover_all returns a list."""
        with patch("snapcast_mvp.core.discovery.Zeroconf"), patch(
            "snapcast_mvp.core.discovery.ServiceBrowser"
        ):
            result = ServerDiscovery.discover_all(timeout=0.1)
            assert isinstance(result, list)
