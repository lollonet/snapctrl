"""Configuration manager using QSettings for persistent storage."""

import logging
from typing import cast

from PySide6.QtCore import QSettings

from snapctrl.models.profile import ServerProfile

logger = logging.getLogger(__name__)

# Settings keys
_KEY_SERVERS = "servers"
_KEY_LAST_SERVER = "last_server"
_KEY_AUTO_CONNECT = "auto_connect_enabled"

# Appearance
_KEY_THEME = "appearance/theme"

# Monitoring
_KEY_PING_INTERVAL = "monitoring/ping_interval"
_KEY_TIME_STATS_INTERVAL = "monitoring/time_stats_interval"

# MPD
_KEY_MPD_HOST = "mpd/host"
_KEY_MPD_PORT = "mpd/port"
_KEY_MPD_POLL_INTERVAL = "mpd/poll_interval"

# Snapclient settings keys
_KEY_SNAPCLIENT_ENABLED = "snapclient/enabled"
_KEY_SNAPCLIENT_BINARY_PATH = "snapclient/binary_path"
_KEY_SNAPCLIENT_AUTO_START = "snapclient/auto_start"
_KEY_SNAPCLIENT_SERVER_HOST = "snapclient/server_host"
_KEY_SNAPCLIENT_EXTRA_ARGS = "snapclient/extra_args"


class ConfigManager:
    """Wrapper around QSettings for type-safe config access.

    QSettings stores config in platform-specific locations:
    - Windows: HKEY_CURRENT_USER\\Software\\SnapCTRL\\SnapCTRL
    - macOS: ~/Library/Preferences/com.SnapCTRL.SnapCTRL.plist
    - Linux: ~/.config/SnapCTRL/SnapCTRL.conf

    Example:
        config = ConfigManager()
        profiles = config.get_server_profiles()
        config.save_server_profiles(profiles)
    """

    def __init__(self, organization: str = "SnapCTRL", application: str = "SnapCTRL") -> None:
        """Initialize the config manager.

        Args:
            organization: Organization name for QSettings.
            application: Application name for QSettings.
        """
        self._settings = QSettings(organization, application)

    @property
    def settings(self) -> QSettings:
        """Return the underlying QSettings instance."""
        return self._settings

    def get_server_profiles(self) -> list[ServerProfile]:
        """Load saved server profiles.

        Returns:
            List of ServerProfile objects, or empty list if none saved.
        """
        raw_data = self._settings.value(_KEY_SERVERS, [], list)
        profiles: list[ServerProfile] = []

        if not isinstance(raw_data, list):
            return profiles

        # Cast to list[object] after isinstance check to satisfy type checker
        data = cast(list[object], raw_data)
        for raw_item in data:
            if not isinstance(raw_item, dict):
                continue
            # After isinstance check, we know it's a dict
            item = cast(dict[str, object], raw_item)
            try:
                id_val = item.get("id", "")
                name_val = item.get("name", "")
                host_val = item.get("host", "")
                port_val = item.get("port", 1705)
                auto_val = item.get("auto_connect", False)
                profiles.append(
                    ServerProfile(
                        id=str(id_val) if id_val else "",
                        name=str(name_val) if name_val else "",
                        host=str(host_val) if host_val else "",
                        port=int(port_val) if isinstance(port_val, int) else 1705,
                        auto_connect=bool(auto_val),
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                logger.warning("Skipping invalid server profile entry: %s", e)
                continue

        return profiles

    def save_server_profiles(self, profiles: list[ServerProfile]) -> None:
        """Persist server profiles.

        Args:
            profiles: List of ServerProfile objects to save.
        """
        data = [
            {
                "id": p.id,
                "name": p.name,
                "host": p.host,
                "port": p.port,
                "auto_connect": p.auto_connect,
            }
            for p in profiles
        ]
        self._settings.setValue(_KEY_SERVERS, data)

    def add_server_profile(self, profile: ServerProfile) -> None:
        """Add a server profile (replacing if ID exists).

        Args:
            profile: ServerProfile to add.
        """
        profiles = self.get_server_profiles()
        # Remove existing with same ID
        profiles = [p for p in profiles if p.id != profile.id]
        # Add new profile
        profiles.append(profile)
        self.save_server_profiles(profiles)

    def remove_server_profile(self, profile_id: str) -> bool:
        """Remove a server profile by ID.

        Args:
            profile_id: ID of the profile to remove.

        Returns:
            True if profile was removed, False if not found.
        """
        profiles = self.get_server_profiles()
        original_count = len(profiles)
        profiles = [p for p in profiles if p.id != profile_id]

        if len(profiles) < original_count:
            self.save_server_profiles(profiles)
            return True
        return False

    def get_profile(self, profile_id: str) -> ServerProfile | None:
        """Get a server profile by ID.

        Args:
            profile_id: ID of the profile to find.

        Returns:
            ServerProfile if found, else None.
        """
        for profile in self.get_server_profiles():
            if profile.id == profile_id:
                return profile
        return None

    def get_last_server_id(self) -> str | None:
        """Get the last connected server ID.

        Returns:
            Server ID string, or None if no last server.
        """
        value = self._settings.value(_KEY_LAST_SERVER, None, str)
        return str(value) if value else None

    def set_last_server_id(self, server_id: str) -> None:
        """Set the last connected server ID.

        Args:
            server_id: Server ID to save.
        """
        self._settings.setValue(_KEY_LAST_SERVER, server_id)

    def get_auto_connect_profile(self) -> ServerProfile | None:
        """Get the profile marked for auto-connect.

        If multiple profiles have auto_connect=True, returns the first one.

        Returns:
            ServerProfile marked for auto-connect, or None.
        """
        for profile in self.get_server_profiles():
            if profile.auto_connect:
                return profile
        return None

    # -- Snapclient settings --------------------------------------------------

    def get_snapclient_enabled(self) -> bool:
        """Return whether the local snapclient is enabled.

        Returns:
            True if local snapclient management is enabled.
        """
        return bool(self._settings.value(_KEY_SNAPCLIENT_ENABLED, False, bool))

    def set_snapclient_enabled(self, enabled: bool) -> None:
        """Enable or disable local snapclient management.

        Args:
            enabled: Whether to enable local snapclient.
        """
        self._settings.setValue(_KEY_SNAPCLIENT_ENABLED, enabled)

    def get_snapclient_binary_path(self) -> str:
        """Return the user-configured snapclient binary path.

        Returns:
            Path string, or empty string for auto-detection.
        """
        value = self._settings.value(_KEY_SNAPCLIENT_BINARY_PATH, "", str)
        return str(value) if value else ""

    def set_snapclient_binary_path(self, path: str) -> None:
        """Set a custom snapclient binary path.

        Args:
            path: Path to binary, or empty string for auto-detection.
        """
        self._settings.setValue(_KEY_SNAPCLIENT_BINARY_PATH, path)

    def get_snapclient_auto_start(self) -> bool:
        """Return whether snapclient should auto-start with the app.

        Returns:
            True if auto-start is enabled (default True).
        """
        return bool(self._settings.value(_KEY_SNAPCLIENT_AUTO_START, True, bool))

    def set_snapclient_auto_start(self, enabled: bool) -> None:
        """Enable or disable snapclient auto-start.

        Args:
            enabled: Whether to auto-start on app launch.
        """
        self._settings.setValue(_KEY_SNAPCLIENT_AUTO_START, enabled)

    def get_snapclient_server_host(self) -> str:
        """Return the server host for snapclient to connect to.

        Returns:
            Host string, or empty string to use the main connection host.
        """
        value = self._settings.value(_KEY_SNAPCLIENT_SERVER_HOST, "", str)
        return str(value) if value else ""

    def set_snapclient_server_host(self, host: str) -> None:
        """Set the server host for snapclient.

        Args:
            host: Hostname or IP, or empty string for main connection host.
        """
        self._settings.setValue(_KEY_SNAPCLIENT_SERVER_HOST, host)

    def get_snapclient_extra_args(self) -> str:
        """Return additional CLI arguments for snapclient.

        Returns:
            Extra arguments string, or empty string.
        """
        value = self._settings.value(_KEY_SNAPCLIENT_EXTRA_ARGS, "", str)
        return str(value) if value else ""

    def set_snapclient_extra_args(self, args: str) -> None:
        """Set additional CLI arguments for snapclient.

        Args:
            args: Extra CLI arguments string.
        """
        self._settings.setValue(_KEY_SNAPCLIENT_EXTRA_ARGS, args)

    # -- Appearance settings ---------------------------------------------------

    def get_theme(self) -> str:
        """Return the theme preference.

        Returns:
            One of "system", "dark", "light". Default "system".
        """
        value = self._settings.value(_KEY_THEME, "system", str)
        return str(value) if value in ("system", "dark", "light") else "system"

    def set_theme(self, theme: str) -> None:
        """Set the theme preference.

        Args:
            theme: One of "system", "dark", "light".
        """
        self._settings.setValue(_KEY_THEME, theme)

    # -- Monitoring settings ---------------------------------------------------

    def get_ping_interval(self) -> int:
        """Return the ping interval in seconds.

        Returns:
            Interval in seconds (default 15).
        """
        value = self._settings.value(_KEY_PING_INTERVAL, 15, int)
        return max(5, min(120, int(value)))  # type: ignore[arg-type]

    def set_ping_interval(self, seconds: int) -> None:
        """Set the ping interval.

        Args:
            seconds: Interval in seconds (5-120).
        """
        self._settings.setValue(_KEY_PING_INTERVAL, max(5, min(120, seconds)))

    def get_time_stats_interval(self) -> int:
        """Return the time stats polling interval in seconds.

        Returns:
            Interval in seconds (default 15).
        """
        value = self._settings.value(_KEY_TIME_STATS_INTERVAL, 15, int)
        return max(5, min(120, int(value)))  # type: ignore[arg-type]

    def set_time_stats_interval(self, seconds: int) -> None:
        """Set the time stats polling interval.

        Args:
            seconds: Interval in seconds (5-120).
        """
        self._settings.setValue(_KEY_TIME_STATS_INTERVAL, max(5, min(120, seconds)))

    # -- MPD settings ----------------------------------------------------------

    def get_mpd_host(self) -> str:
        """Return the MPD host.

        Returns:
            Host string, or empty string to use the Snapcast server host.
        """
        value = self._settings.value(_KEY_MPD_HOST, "", str)
        return str(value) if value else ""

    def set_mpd_host(self, host: str) -> None:
        """Set the MPD host.

        Args:
            host: Hostname or IP, or empty string for Snapcast server host.
        """
        self._settings.setValue(_KEY_MPD_HOST, host)

    def get_mpd_port(self) -> int:
        """Return the MPD port.

        Returns:
            Port number (default 6600).
        """
        value = self._settings.value(_KEY_MPD_PORT, 6600, int)
        return max(1, min(65535, int(value)))  # type: ignore[arg-type]

    def set_mpd_port(self, port: int) -> None:
        """Set the MPD port.

        Args:
            port: Port number (1-65535).
        """
        self._settings.setValue(_KEY_MPD_PORT, max(1, min(65535, port)))

    def get_mpd_poll_interval(self) -> int:
        """Return the MPD poll interval in seconds.

        Returns:
            Interval in seconds (default 2).
        """
        value = self._settings.value(_KEY_MPD_POLL_INTERVAL, 2, int)
        return max(1, min(30, int(value)))  # type: ignore[arg-type]

    def set_mpd_poll_interval(self, seconds: int) -> None:
        """Set the MPD poll interval.

        Args:
            seconds: Interval in seconds (1-30).
        """
        self._settings.setValue(_KEY_MPD_POLL_INTERVAL, max(1, min(30, seconds)))

    # -- General settings ------------------------------------------------------

    def clear(self) -> None:
        """Clear all settings (useful for testing or reset)."""
        self._settings.clear()

    def sync(self) -> None:
        """Force settings to be written to disk."""
        self._settings.sync()
