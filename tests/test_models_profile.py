"""Tests for ServerProfile model."""

import pytest

from snapcast_mvp.models.profile import ServerProfile, create_profile


class TestServerProfile:
    """Test ServerProfile dataclass."""

    def test_creation_with_defaults(self) -> None:
        """Test profile creation with default port and auto_connect."""
        profile = ServerProfile(
            id="test-1",
            name="Test Server",
            host="192.168.1.100",
        )
        assert profile.id == "test-1"
        assert profile.name == "Test Server"
        assert profile.host == "192.168.1.100"
        assert profile.port == 1705
        assert profile.auto_connect is False

    def test_creation_with_all_params(self) -> None:
        """Test profile creation with all parameters."""
        profile = ServerProfile(
            id="test-2",
            name="Living Room",
            host="snapcast.local",
            port=1704,
            auto_connect=True,
        )
        assert profile.id == "test-2"
        assert profile.name == "Living Room"
        assert profile.host == "snapcast.local"
        assert profile.port == 1704
        assert profile.auto_connect is True

    def test_with_auto_connect(self) -> None:
        """Test creating a copy with different auto_connect value."""
        profile = ServerProfile(
            id="test-1",
            name="Test",
            host="192.168.1.100",
            auto_connect=False,
        )
        updated = profile.with_auto_connect(True)

        assert updated.id == profile.id
        assert updated.name == profile.name
        assert updated.host == profile.host
        assert updated.port == profile.port
        assert updated.auto_connect is True
        # Original unchanged (frozen)
        assert profile.auto_connect is False

    def test_is_immutable(self) -> None:
        """Test that ServerProfile is frozen."""
        profile = ServerProfile(
            id="test-1",
            name="Test",
            host="192.168.1.100",
        )
        with pytest.raises(Exception):  # FrozenInstanceError
            profile.name = "Changed"

    def test_equality(self) -> None:
        """Test profile equality."""
        p1 = ServerProfile(id="x", name="A", host="a")
        p2 = ServerProfile(id="x", name="A", host="a")
        p3 = ServerProfile(id="y", name="A", host="a")

        assert p1 == p2
        assert p1 != p3


class TestCreateProfile:
    """Test create_profile factory function."""

    def test_creates_profile_with_id(self) -> None:
        """Test that create_profile generates an ID."""
        profile = create_profile("My Server", "192.168.1.100")
        assert profile.id is not None
        assert len(profile.id) == 8  # MD5 hash prefix
        assert profile.name == "My Server"
        assert profile.host == "192.168.1.100"

    def test_same_host_port_same_id(self) -> None:
        """Test that same host:port generates same ID."""
        p1 = create_profile("Server 1", "192.168.1.100", 1705)
        p2 = create_profile("Server 2", "192.168.1.100", 1705)
        assert p1.id == p2.id

    def test_different_port_different_id(self) -> None:
        """Test that different port generates different ID."""
        p1 = create_profile("Server", "192.168.1.100", 1705)
        p2 = create_profile("Server", "192.168.1.100", 1704)
        assert p1.id != p2.id

    def test_with_all_params(self) -> None:
        """Test create_profile with all parameters."""
        profile = create_profile(
            "Living Room",
            "snapcast.local",
            port=1704,
            auto_connect=True,
        )
        assert profile.name == "Living Room"
        assert profile.host == "snapcast.local"
        assert profile.port == 1704
        assert profile.auto_connect is True
