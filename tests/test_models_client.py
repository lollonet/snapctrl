"""Tests for Client model."""

import time

import pytest

from snapctrl.models.client import Client


class TestClient:
    """Tests for Client dataclass."""

    def test_client_creation_with_defaults(self) -> None:
        """Test creating a client with default values."""
        client = Client(id="client-1", host="192.168.1.50")
        assert client.id == "client-1"
        assert client.host == "192.168.1.50"
        assert client.name == ""
        assert client.mac == ""
        assert client.volume == 50
        assert client.muted is False
        assert client.connected is True
        assert client.latency == 0
        assert client.snapclient_version == ""

    def test_client_creation_with_all_params(self) -> None:
        """Test creating a client with all parameters."""
        client = Client(
            id="client-2",
            host="10.0.0.25",
            name="Kitchen Speaker",
            mac="AA:BB:CC:DD:EE:FF",
            volume=75,
            muted=True,
            connected=False,
            latency=150,
            snapclient_version="0.27.0",
        )
        assert client.id == "client-2"
        assert client.host == "10.0.0.25"
        assert client.name == "Kitchen Speaker"
        assert client.mac == "AA:BB:CC:DD:EE:FF"
        assert client.volume == 75
        assert client.muted is True
        assert client.connected is False
        assert client.latency == 150
        assert client.snapclient_version == "0.27.0"

    def test_display_name_with_name(self) -> None:
        """Test display_name returns name when set."""
        client = Client(id="client-1", host="192.168.1.50", name="Living Room")
        assert client.display_name == "Living Room"

    def test_display_name_fallback_to_host(self) -> None:
        """Test display_name falls back to host when name is empty."""
        client = Client(id="client-1", host="192.168.1.50", name="")
        assert client.display_name == "192.168.1.50"

    def test_is_muted_alias(self) -> None:
        """Test is_muted is an alias for muted."""
        client = Client(id="client-1", host="192.168.1.50", muted=True)
        assert client.is_muted is True

    def test_is_connected_alias(self) -> None:
        """Test is_connected is an alias for connected."""
        client = Client(id="client-1", host="192.168.1.50", connected=False)
        assert client.is_connected is False

    def test_client_is_immutable(self) -> None:
        """Test that Client instances are immutable (frozen)."""
        client = Client(id="client-1", host="192.168.1.50")
        with pytest.raises(Exception):  # FrozenInstanceError
            client.volume = 75  # type: ignore[misc]

    def test_client_volume_range(self) -> None:
        """Test client volume is clamped to 0-100 range."""
        client_low = Client(id="client-1", host="192.168.1.50", volume=0)
        client_high = Client(id="client-2", host="192.168.1.51", volume=100)
        client_over = Client(id="client-3", host="192.168.1.52", volume=150)
        client_under = Client(id="client-4", host="192.168.1.53", volume=-10)

        assert client_low.volume == 0
        assert client_high.volume == 100
        assert client_over.volume == 100  # Clamped from 150
        assert client_under.volume == 0  # Clamped from -10

    def test_client_equality(self) -> None:
        """Test client equality comparison."""
        client1 = Client(id="client-1", host="192.168.1.50", volume=50)
        client2 = Client(id="client-1", host="192.168.1.50", volume=50)
        client3 = Client(id="client-1", host="192.168.1.50", volume=75)

        assert client1 == client2
        assert client1 != client3


class TestClientLastSeenAgo:
    """Tests for last_seen_ago property."""

    def test_last_seen_ago_unknown(self) -> None:
        """Test last_seen_ago returns 'unknown' when last_seen_sec is 0."""
        client = Client(id="client-1", host="192.168.1.50", last_seen_sec=0)
        assert client.last_seen_ago == "unknown"

    def test_last_seen_ago_just_now(self) -> None:
        """Test last_seen_ago returns 'just now' for recent clients."""
        client = Client(
            id="client-1",
            host="192.168.1.50",
            last_seen_sec=int(time.time()) - 1,  # 1 second ago
        )
        assert client.last_seen_ago == "just now"

    def test_last_seen_ago_seconds(self) -> None:
        """Test last_seen_ago returns seconds ago."""
        client = Client(
            id="client-1",
            host="192.168.1.50",
            last_seen_sec=int(time.time()) - 30,  # 30 seconds ago
        )
        assert "s ago" in client.last_seen_ago

    def test_last_seen_ago_minutes(self) -> None:
        """Test last_seen_ago returns minutes ago."""
        client = Client(
            id="client-1",
            host="192.168.1.50",
            last_seen_sec=int(time.time()) - 300,  # 5 minutes ago
        )
        assert "m ago" in client.last_seen_ago

    def test_last_seen_ago_hours(self) -> None:
        """Test last_seen_ago returns hours ago."""
        client = Client(
            id="client-1",
            host="192.168.1.50",
            last_seen_sec=int(time.time()) - 7200,  # 2 hours ago
        )
        assert "h ago" in client.last_seen_ago

    def test_last_seen_ago_days(self) -> None:
        """Test last_seen_ago returns days ago."""
        client = Client(
            id="client-1",
            host="192.168.1.50",
            last_seen_sec=int(time.time()) - 172800,  # 2 days ago
        )
        assert "d ago" in client.last_seen_ago


class TestClientDisplaySystem:
    """Tests for display_system property."""

    def test_display_system_both(self) -> None:
        """Test display_system with both OS and arch."""
        client = Client(id="client-1", host="192.168.1.50", host_os="Linux", host_arch="aarch64")
        assert client.display_system == "Linux / aarch64"

    def test_display_system_os_only(self) -> None:
        """Test display_system with OS only."""
        client = Client(id="client-1", host="192.168.1.50", host_os="macOS")
        assert client.display_system == "macOS"

    def test_display_system_arch_only(self) -> None:
        """Test display_system with arch only."""
        client = Client(id="client-1", host="192.168.1.50", host_arch="x86_64")
        assert client.display_system == "x86_64"

    def test_display_system_empty(self) -> None:
        """Test display_system returns empty when neither is set."""
        client = Client(id="client-1", host="192.168.1.50")
        assert client.display_system == ""


class TestClientDisplayLatency:
    """Tests for display_latency property."""

    def test_display_latency_zero(self) -> None:
        """Test display_latency with zero offset."""
        client = Client(id="client-1", host="192.168.1.50", latency=0)
        assert client.display_latency == "0ms (no offset)"

    def test_display_latency_positive(self) -> None:
        """Test display_latency with positive offset."""
        client = Client(id="client-1", host="192.168.1.50", latency=150)
        assert client.display_latency == "150ms"

    def test_display_latency_negative(self) -> None:
        """Test display_latency with negative offset."""
        client = Client(id="client-1", host="192.168.1.50", latency=-50)
        assert client.display_latency == "-50ms"
