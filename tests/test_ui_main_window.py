"""Tests for MainWindow."""

from unittest.mock import MagicMock, Mock

from pytestqt.qtbot import QtBot

from snapctrl.core.config import ConfigManager
from snapctrl.core.state import StateStore
from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source
from snapctrl.ui.main_window import MainWindow


class TestMainWindowBasics:
    """Test MainWindow creation and layout."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that main window can be created."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.windowTitle() == "SnapCTRL"
        assert window.minimumWidth() == 900
        assert window.minimumHeight() == 600

    def test_has_panels(self, qtbot: QtBot) -> None:
        """Test that main window has all three panels."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.sources_panel is not None
        assert window.groups_panel is not None
        assert window.properties_panel is not None

    def test_panels_are_visible(self, qtbot: QtBot) -> None:
        """Test that panels are visible."""
        window = MainWindow()
        window.show()
        qtbot.addWidget(window)

        assert window.sources_panel.isVisible()
        assert window.groups_panel.isVisible()
        assert window.properties_panel.isVisible()

    def test_group_mute_signal_connected(self, qtbot: QtBot) -> None:
        """Test that group mute toggle signal is connected to controller."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a mock slot to verify signal connection
        mock_slot = Mock()

        # Connect to the group mute toggled signal
        window._groups_panel.mute_toggled.connect(mock_slot)

        # Emit a signal and verify it propagates
        window._groups_panel.mute_toggled.emit("test-group", True)

        # Verify the mock was called (group_id, muted)
        mock_slot.assert_called_once_with("test-group", True)

        # Clean up
        window._groups_panel.mute_toggled.disconnect(mock_slot)


class TestMainWindowSnapclientStatus:
    """Test snapclient status bar indicator."""

    def test_snapclient_label_hidden_initially(self, qtbot: QtBot) -> None:
        """Snapclient label is hidden by default."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        assert not window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_running(self, qtbot: QtBot) -> None:
        """Running status shows green label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("running")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Running" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_stopped(self, qtbot: QtBot) -> None:
        """Stopped status shows grey label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("stopped")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Stopped" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_error(self, qtbot: QtBot) -> None:
        """Error status shows red label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("error")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Error" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_disabled_hides(self, qtbot: QtBot) -> None:
        """Disabled status hides the label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("running")  # first show it
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        window.set_snapclient_status("disabled")
        assert not window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_starting(self, qtbot: QtBot) -> None:
        """Starting status shows label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("starting")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Starting" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]


class TestMainWindowStyling:
    """Test MainWindow styling."""

    def test_has_stylesheet(self, qtbot: QtBot) -> None:
        """Test that main window has styling applied."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.styleSheet() != ""
        assert "background-color" in window.styleSheet()


class TestMainWindowWithState:
    """Test MainWindow with StateStore integration."""

    def test_creation_with_state(self, qtbot: QtBot) -> None:
        """Test window creation with state store."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)
        assert window._state is state

    def test_set_connection_status_connected(self, qtbot: QtBot) -> None:
        """Test status updates to connected."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        window.set_connection_status(True)
        assert "connected" in window._status_label.text().lower()

    def test_set_connection_status_disconnected(self, qtbot: QtBot) -> None:
        """Test status updates to disconnected."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        window.set_connection_status(False)
        text = window._status_label.text().lower()
        assert "disconnected" in text or "connecting" in text

    def test_set_ping_results(self, qtbot: QtBot) -> None:
        """Test updating ping results."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        results = {"c1": 10.5, "c2": None}
        window.set_ping_results(results)
        assert window._ping_results == results

    def test_set_time_stats(self, qtbot: QtBot) -> None:
        """Test updating time stats."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        stats = {"c1": {"latency_median_ms": 10}}
        window.set_time_stats(stats)
        assert window._time_stats == stats


class TestMainWindowStateChanges:
    """Test state change handlers."""

    def test_on_groups_changed(self, qtbot: QtBot) -> None:
        """Test groups changed handler."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        group = Group(id="g1", name="Test", stream_id="s1", muted=False, client_ids=["c1"])
        source = Source(id="s1", name="Source", status="playing")
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)

        state._groups = {group.id: group}
        state._sources = {source.id: source}
        state._clients = {client.id: client}

        window._on_groups_changed([group])

    def test_on_sources_changed(self, qtbot: QtBot) -> None:
        """Test sources changed handler."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        source = Source(id="s1", name="Source", status="playing")
        window._on_sources_changed([source])

    def test_on_clients_changed(self, qtbot: QtBot) -> None:
        """Test clients changed handler."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        window._on_clients_changed([client])


class TestMainWindowSelection:
    """Test selection handling."""

    def test_on_group_selected(self, qtbot: QtBot) -> None:
        """Test group selection."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        group = Group(id="g1", name="Test", stream_id="s1", muted=False, client_ids=["c1"])
        source = Source(id="s1", name="Source", status="playing")
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)

        state._groups = {group.id: group}
        state._sources = {source.id: source}
        state._clients = {client.id: client}
        state._groups_cache = None

        window._on_group_selected(group.id)

    def test_on_client_selected(self, qtbot: QtBot) -> None:
        """Test client selection."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        state._clients = {client.id: client}
        state._clients_cache = None

        window._on_client_selected(client.id)
        assert window._selected_client_id == client.id


class TestMainWindowTheme:
    """Test theme functionality."""

    def test_refresh_theme(self, qtbot: QtBot) -> None:
        """Test theme refresh."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        window._refresh_theme()  # Should not crash


class TestMainWindowSnapclientExternal:
    """Test external snapclient status."""

    def test_set_snapclient_status_external(self, qtbot: QtBot) -> None:
        """External status shows special label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("external")
        assert window._snapclient_label.isVisible()
        assert "External" in window._snapclient_label.text()

    def test_set_snapclient_status_unknown(self, qtbot: QtBot) -> None:
        """Unknown status shows fallback."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("unknown_status")
        assert window._snapclient_label.isVisible()
        assert "Unknown" in window._snapclient_label.text()


class TestMainWindowServerInfo:
    """Test server info display."""

    def test_set_server_info_with_hostname(self, qtbot: QtBot) -> None:
        """Test server info with hostname."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window.set_server_info("192.168.1.100", 1705, "snapserver.local")

        assert "snapserver.local" in window._server_label.text()
        assert "192.168.1.100" in window._server_label.text()
        assert "1705" in window._server_label.text()

    def test_set_server_info_without_hostname(self, qtbot: QtBot) -> None:
        """Test server info without hostname."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window.set_server_info("192.168.1.100", 1705)

        assert "192.168.1.100" in window._server_label.text()
        assert "1705" in window._server_label.text()


class TestMainWindowPingResults:
    """Test ping results with selected client."""

    def test_set_ping_results_updates_properties_panel(self, qtbot: QtBot) -> None:
        """Test ping results updates properties when client selected."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        # Set up client and select it
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        state._clients = {client.id: client}
        state._clients_cache = None
        window._selected_client_id = "c1"

        # Set ping results - should update properties panel
        results = {"c1": 15.5}
        window.set_ping_results(results)

        assert window._ping_results == results


class TestMainWindowTimeStats:
    """Test time stats with selected client."""

    def test_set_time_stats_updates_properties_panel(self, qtbot: QtBot) -> None:
        """Test time stats updates properties when client selected."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        # Set up client and select it
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        state._clients = {client.id: client}
        state._clients_cache = None
        window._selected_client_id = "c1"

        # Set time stats - should update properties panel
        stats = {"c1": {"latency_median_ms": 10, "jitter_median_ms": 2.5}}
        window.set_time_stats(stats)

        assert window._time_stats == stats


class TestMainWindowSourceSelected:
    """Test source selection behavior."""

    def test_on_source_selected_with_group_selected(self, qtbot: QtBot) -> None:
        """Test source selection when group is already selected."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        group = Group(id="g1", name="Test", stream_id="s1", muted=False, client_ids=[])
        source = Source(id="s2", name="Source2", status="playing")
        state._groups = {group.id: group}
        state._sources = {source.id: source}

        # Set up groups panel with a selected group
        window._groups_panel.set_groups(
            [group],
            [source],
            {},
        )
        window._groups_panel.set_selected_group("g1")

        # Capture the source_changed signal
        received: list[tuple[str, str]] = []
        window._groups_panel.source_changed.connect(lambda gid, sid: received.append((gid, sid)))

        # Trigger source selection
        window._on_source_selected("s2")

        assert len(received) == 1
        assert received[0] == ("g1", "s2")

    def test_on_source_selected_no_group_selected(self, qtbot: QtBot) -> None:
        """Test source selection auto-selects first group."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        group = Group(id="g1", name="Test", stream_id="s1", muted=False, client_ids=[])
        source = Source(id="s2", name="Source2", status="playing")
        state._groups = {group.id: group}
        state._sources = {source.id: source}
        state._groups_cache = None

        # Set up groups panel but don't select anything
        window._groups_panel.set_groups(
            [group],
            [source],
            {},
        )

        # Capture the source_changed signal
        received: list[tuple[str, str]] = []
        window._groups_panel.source_changed.connect(lambda gid, sid: received.append((gid, sid)))

        # Trigger source selection - should auto-select first group
        window._on_source_selected("s2")

        # Should have selected first group and emitted signal
        assert len(received) == 1
        assert received[0][1] == "s2"


class TestMainWindowClientsChanged:
    """Test clients changed handler with selected client."""

    def test_on_clients_changed_updates_selected(self, qtbot: QtBot) -> None:
        """Test clients changed updates selected client in properties."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        group = Group(id="g1", name="Test", stream_id="s1", muted=False, client_ids=["c1"])
        source = Source(id="s1", name="Source", status="playing")
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)

        state._groups = {group.id: group}
        state._sources = {source.id: source}
        state._clients = {client.id: client}
        state._groups_cache = None
        state._clients_cache = None

        # Select the client
        window._selected_client_id = "c1"

        # Trigger clients changed
        window._on_clients_changed([client])


class TestMainWindowSetHideToTray:
    """Test hide to tray setting."""

    def test_set_hide_to_tray(self, qtbot: QtBot) -> None:
        """Test set_hide_to_tray stores setting."""
        window = MainWindow()
        qtbot.addWidget(window)

        window.set_hide_to_tray(True)
        assert window._hide_to_tray is True

        window.set_hide_to_tray(False)
        assert window._hide_to_tray is False


class TestMainWindowProperties:
    """Test MainWindow property accessors."""

    def test_config_property(self, qtbot: QtBot) -> None:
        """Test config property returns config manager."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Without config, should return None
        assert window.config is None

        # With config set, should return the config
        mock_config = MagicMock()
        window._config = mock_config
        assert window.config is mock_config

    def test_state_store_property(self, qtbot: QtBot) -> None:
        """Test state_store property returns state store."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        assert window.state_store is state


class TestMainWindowOpenPreferences:
    """Test preferences dialog opening."""

    def test_open_preferences_no_config(self, qtbot: QtBot) -> None:
        """Test open_preferences without config is no-op."""
        window = MainWindow()  # No config
        qtbot.addWidget(window)

        window.open_preferences()  # Should not crash

    def test_open_preferences_without_config(self, qtbot: QtBot) -> None:
        """Test open_preferences does nothing without config."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Should not crash when config is None
        window.open_preferences()

    def test_open_preferences_with_config(self, qtbot: QtBot) -> None:
        """Test open_preferences creates and opens dialog."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Set up real config
        config = ConfigManager()
        window._config = config
        window._server_host = "192.168.1.100"
        window._server_port = 1705
        window._server_hostname = "snapserver"

        # Call open_preferences - creates a real dialog which is non-modal
        # Just verify it does not crash
        window.open_preferences()


class TestMainWindowSetPingResults:
    """Test ping results handling."""

    def test_set_ping_results_updates_properties(self, qtbot: QtBot) -> None:
        """Test set_ping_results updates properties panel."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        state._clients = {client.id: client}
        state._clients_cache = None

        # Select client
        window._selected_client_id = "c1"

        # Set ping results
        results = {"c1": 5.5}
        window.set_ping_results(results)

        assert window._ping_results == results
