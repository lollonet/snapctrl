"""Tests for Client model."""

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
        """Test client can have any volume value (validation elsewhere)."""
        # Model doesn't enforce range - validation is higher layer
        client_low = Client(id="client-1", host="192.168.1.50", volume=0)
        client_high = Client(id="client-2", host="192.168.1.51", volume=100)
        client_over = Client(id="client-3", host="192.168.1.52", volume=150)

        assert client_low.volume == 0
        assert client_high.volume == 100
        assert client_over.volume == 150

    def test_client_equality(self) -> None:
        """Test client equality comparison."""
        client1 = Client(id="client-1", host="192.168.1.50", volume=50)
        client2 = Client(id="client-1", host="192.168.1.50", volume=50)
        client3 = Client(id="client-1", host="192.168.1.50", volume=75)

        assert client1 == client2
        assert client1 != client3
