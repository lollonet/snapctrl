"""Tests for ConfigManager using QSettings."""

import pytest

from snapctrl.core.config import ConfigManager
from snapctrl.models.profile import ServerProfile, create_profile


@pytest.fixture
def config() -> ConfigManager:
    """Return a fresh ConfigManager for each test."""
    # Use unique organization/app to avoid test interference
    config = ConfigManager("SnapcastMVPTest", "TestConfig")
    config.clear()
    return config


class TestConfigManagerBasics:
    """Test basic ConfigManager functionality."""

    def test_initially_empty(self, config: ConfigManager) -> None:
        """Test that config starts empty."""
        assert config.get_server_profiles() == []

    def test_save_and_load_profiles(self, config: ConfigManager) -> None:
        """Test saving and loading server profiles."""
        profiles = [
            ServerProfile(id="p1", name="Living Room", host="192.168.1.100"),
            ServerProfile(id="p2", name="Basement", host="192.168.1.101", port=1704),
        ]
        config.save_server_profiles(profiles)

        loaded = config.get_server_profiles()
        assert len(loaded) == 2
        assert loaded[0].id == "p1"
        assert loaded[0].name == "Living Room"
        assert loaded[0].host == "192.168.1.100"
        assert loaded[1].id == "p2"
        assert loaded[1].port == 1704

    def test_add_profile(self, config: ConfigManager) -> None:
        """Test adding a single profile."""
        profile = create_profile("Test", "192.168.1.100")
        config.add_server_profile(profile)

        loaded = config.get_server_profiles()
        assert len(loaded) == 1
        assert loaded[0].id == profile.id
        assert loaded[0].name == "Test"

    def test_add_replaces_same_id(self, config: ConfigManager) -> None:
        """Test that adding a profile replaces one with same ID."""
        p1 = ServerProfile(id="abc", name="Old Name", host="192.168.1.100")
        p2 = ServerProfile(id="abc", name="New Name", host="192.168.1.100")
        config.add_server_profile(p1)
        config.add_server_profile(p2)

        loaded = config.get_server_profiles()
        assert len(loaded) == 1
        assert loaded[0].name == "New Name"

    def test_remove_profile(self, config: ConfigManager) -> None:
        """Test removing a profile."""
        p1 = ServerProfile(id="p1", name="Server 1", host="a")
        p2 = ServerProfile(id="p2", name="Server 2", host="b")
        config.save_server_profiles([p1, p2])

        assert config.remove_server_profile("p1") is True
        assert config.remove_server_profile("nonexistent") is False

        loaded = config.get_server_profiles()
        assert len(loaded) == 1
        assert loaded[0].id == "p2"

    def test_get_profile(self, config: ConfigManager) -> None:
        """Test getting a profile by ID."""
        profile = ServerProfile(id="xyz", name="Target", host="host")
        config.add_server_profile(profile)

        found = config.get_profile("xyz")
        assert found is not None
        assert found.name == "Target"

        not_found = config.get_profile("nonexistent")
        assert not_found is None


class TestConfigManagerLastServer:
    """Test last server tracking."""

    def test_last_server_initially_none(self, config: ConfigManager) -> None:
        """Test that last server is None initially."""
        assert config.get_last_server_id() is None

    def test_set_and_get_last_server(self, config: ConfigManager) -> None:
        """Test setting and getting last server ID."""
        config.set_last_server_id("server-123")
        assert config.get_last_server_id() == "server-123"

    def test_override_last_server(self, config: ConfigManager) -> None:
        """Test overriding last server ID."""
        config.set_last_server_id("server-1")
        config.set_last_server_id("server-2")
        assert config.get_last_server_id() == "server-2"


class TestConfigManagerAutoConnect:
    """Test auto-connect profile selection."""

    def test_no_auto_connect_returns_none(self, config: ConfigManager) -> None:
        """Test that get_auto_connect_profile returns None when none set."""
        profile = ServerProfile(id="p1", name="Server", host="host", auto_connect=False)
        config.add_server_profile(profile)

        assert config.get_auto_connect_profile() is None

    def test_get_auto_connect_profile(self, config: ConfigManager) -> None:
        """Test getting the auto-connect profile."""
        p1 = ServerProfile(id="p1", name="Server 1", host="a", auto_connect=False)
        p2 = ServerProfile(id="p2", name="Server 2", host="b", auto_connect=True)
        config.save_server_profiles([p1, p2])

        result = config.get_auto_connect_profile()
        assert result is not None
        assert result.id == "p2"

    def test_first_auto_connect_if_multiple(self, config: ConfigManager) -> None:
        """Test that first auto-connect profile is returned if multiple set."""
        p1 = ServerProfile(id="p1", name="S1", host="a", auto_connect=True)
        p2 = ServerProfile(id="p2", name="S2", host="b", auto_connect=True)
        config.save_server_profiles([p1, p2])

        result = config.get_auto_connect_profile()
        assert result is not None
        assert result.id == "p1"


class TestConfigManagerPersistence:
    """Test that config persists across instances."""

    def test_persists_across_instances(self, config: ConfigManager) -> None:
        """Test that data persists when creating new ConfigManager."""
        profile = ServerProfile(id="persist", name="Persist", host="host")
        config.add_server_profile(profile)

        # Create new instance with same org/app
        config2 = ConfigManager("SnapcastMVPTest", "TestConfig")
        loaded = config2.get_server_profiles()

        assert len(loaded) == 1
        assert loaded[0].id == "persist"

        # Cleanup
        config2.clear()


class TestConfigManagerClear:
    """Test clear functionality."""

    def test_clear_removes_all_data(self, config: ConfigManager) -> None:
        """Test that clear removes all settings."""
        profile = ServerProfile(id="x", name="X", host="x")
        config.add_server_profile(profile)
        config.set_last_server_id("x")

        config.clear()

        assert config.get_server_profiles() == []
        assert config.get_last_server_id() is None


class TestConfigManagerSnapclient:
    """Test snapclient configuration settings."""

    def test_snapclient_enabled_default_false(self, config: ConfigManager) -> None:
        """Snapclient is disabled by default."""
        assert config.get_snapclient_enabled() is False

    def test_set_snapclient_enabled(self, config: ConfigManager) -> None:
        """Can enable/disable snapclient."""
        config.set_snapclient_enabled(True)
        assert config.get_snapclient_enabled() is True
        config.set_snapclient_enabled(False)
        assert config.get_snapclient_enabled() is False

    def test_snapclient_binary_path_default_empty(self, config: ConfigManager) -> None:
        """Binary path defaults to empty (auto-detect)."""
        assert config.get_snapclient_binary_path() == ""

    def test_set_snapclient_binary_path(self, config: ConfigManager) -> None:
        """Can set a custom binary path."""
        config.set_snapclient_binary_path("/opt/snapclient")
        assert config.get_snapclient_binary_path() == "/opt/snapclient"

    def test_clear_snapclient_binary_path(self, config: ConfigManager) -> None:
        """Can clear binary path back to auto-detect."""
        config.set_snapclient_binary_path("/opt/snapclient")
        config.set_snapclient_binary_path("")
        assert config.get_snapclient_binary_path() == ""

    def test_snapclient_auto_start_default_true(self, config: ConfigManager) -> None:
        """Auto-start defaults to True."""
        assert config.get_snapclient_auto_start() is True

    def test_set_snapclient_auto_start(self, config: ConfigManager) -> None:
        """Can toggle auto-start."""
        config.set_snapclient_auto_start(False)
        assert config.get_snapclient_auto_start() is False

    def test_snapclient_server_host_default_empty(self, config: ConfigManager) -> None:
        """Server host defaults to empty (use main connection)."""
        assert config.get_snapclient_server_host() == ""

    def test_set_snapclient_server_host(self, config: ConfigManager) -> None:
        """Can set a custom server host."""
        config.set_snapclient_server_host("192.168.1.50")
        assert config.get_snapclient_server_host() == "192.168.1.50"

    def test_snapclient_extra_args_default_empty(self, config: ConfigManager) -> None:
        """Extra args default to empty."""
        assert config.get_snapclient_extra_args() == ""

    def test_set_snapclient_extra_args(self, config: ConfigManager) -> None:
        """Can set extra CLI arguments."""
        config.set_snapclient_extra_args("--latency 100 --mixer pulse")
        assert config.get_snapclient_extra_args() == "--latency 100 --mixer pulse"


class TestConfigManagerInvalidData:
    """Test handling of invalid data in settings."""

    def test_handles_invalid_profile_data(self, config: ConfigManager) -> None:
        """Test that invalid profile entries are skipped."""
        # Manually inject invalid data
        settings = config.settings
        settings.setValue(
            "servers",
            [
                {
                    "id": "valid",
                    "name": "Valid",
                    "host": "host",
                    "port": 1705,
                    "auto_connect": False,
                },
                {"name": "MissingId"},  # Missing required field
                "not a dict",  # Wrong type
                {"id": "", "name": "", "host": ""},  # Empty but valid structure
            ],
        )

        profiles = config.get_server_profiles()
        # Should get the valid one and the empty one
        assert len(profiles) >= 1
        assert any(p.id == "valid" for p in profiles)
