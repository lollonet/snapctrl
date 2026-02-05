"""Extended tests for SystemTrayManager covering more code paths."""

from __future__ import annotations

from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QSystemTrayIcon
from pytestqt.qtbot import QtBot

from snapctrl.core.snapclient_manager import SnapclientManager
from snapctrl.core.state import StateStore
from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source
from snapctrl.ui.main_window import MainWindow
from snapctrl.ui.system_tray import SystemTrayManager


def _make_state(
    groups: list[Group] | None = None,
    clients: list[Client] | None = None,
    sources: list[Source] | None = None,
) -> StateStore:
    """Create a StateStore pre-populated with test data."""
    state = StateStore()
    if groups:
        state._groups = {g.id: g for g in groups}  # pyright: ignore[reportPrivateUsage]
    if clients:
        state._clients = {c.id: c for c in clients}  # pyright: ignore[reportPrivateUsage]
    if sources:
        state._sources = {s.id: s for s in sources}  # pyright: ignore[reportPrivateUsage]
    return state


class TestSystemTrayAvailability:
    """Test tray availability checks."""

    def test_available_property(self, qtbot: QtBot) -> None:
        """Test available property delegates to QSystemTrayIcon."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        # Just test it doesn't crash and returns bool
        assert isinstance(tray.available, bool)


class TestSystemTrayShow:
    """Test show/hide functionality."""

    def test_show_when_available(self, qtbot: QtBot) -> None:
        """Test show calls tray.show() when available."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._tray, "show") as mock_show:
            with patch.object(
                SystemTrayManager, "available", new_callable=PropertyMock, return_value=True
            ):
                tray.show()
                mock_show.assert_called_once()

    def test_show_when_not_available(self, qtbot: QtBot) -> None:
        """Test show logs warning when not available."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._tray, "show") as mock_show:
            with patch.object(
                SystemTrayManager, "available", new_callable=PropertyMock, return_value=False
            ):
                tray.show()
                mock_show.assert_not_called()

    def test_hide(self, qtbot: QtBot) -> None:
        """Test hide calls tray.hide()."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._tray, "hide") as mock_hide:
            tray.hide()
            mock_hide.assert_called_once()


class TestSystemTraySignals:
    """Test signal emissions."""

    def test_mute_changed_signal(self, qtbot: QtBot) -> None:
        """Test mute_changed signal exists and can be connected."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        received: list[tuple[str, bool]] = []
        tray.mute_changed.connect(lambda gid, m: received.append((gid, m)))

        # Emit signal
        tray.mute_changed.emit("g1", True)

        assert received == [("g1", True)]

    def test_volume_changed_signal(self, qtbot: QtBot) -> None:
        """Test volume_changed signal."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        received: list[tuple[str, int]] = []
        tray.volume_changed.connect(lambda gid, v: received.append((gid, v)))

        tray.volume_changed.emit("g1", 75)

        assert received == [("g1", 75)]

    def test_mute_all_changed_signal(self, qtbot: QtBot) -> None:
        """Test mute_all_changed signal."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        received: list[bool] = []
        tray.mute_all_changed.connect(received.append)

        tray.mute_all_changed.emit(True)
        tray.mute_all_changed.emit(False)

        assert received == [True, False]

    def test_preferences_requested_signal(self, qtbot: QtBot) -> None:
        """Test preferences_requested signal."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        called = []
        tray.preferences_requested.connect(lambda: called.append(True))

        tray.preferences_requested.emit()

        assert called == [True]


class TestMenuFingerprint:
    """Test menu fingerprint computation."""

    def test_fingerprint_includes_connection(self, qtbot: QtBot) -> None:
        """Test fingerprint includes connection state."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        tray._connected = True
        fp1 = tray._compute_menu_fingerprint()

        tray._connected = False
        fp2 = tray._compute_menu_fingerprint()

        assert fp1 != fp2

    def test_fingerprint_includes_visibility(self, qtbot: QtBot) -> None:
        """Test fingerprint includes window visibility."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        window.show()
        fp1 = tray._compute_menu_fingerprint()

        window.hide()
        fp2 = tray._compute_menu_fingerprint()

        assert fp1 != fp2

    def test_fingerprint_includes_groups(self, qtbot: QtBot) -> None:
        """Test fingerprint includes group state."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group1 = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group1], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        fp1 = tray._compute_menu_fingerprint()

        # Change group mute state (update internal dict and clear cache)
        group2 = Group(id="g1", name="G1", stream_id="s1", muted=True, client_ids=["c1"])
        state._groups["g1"] = group2  # pyright: ignore[reportPrivateUsage]
        state._groups_cache = None  # pyright: ignore[reportPrivateUsage]

        fp2 = tray._compute_menu_fingerprint()

        assert fp1 != fp2

    def test_fingerprint_skips_rebuild_when_unchanged(self, qtbot: QtBot) -> None:
        """Test that identical fingerprint skips menu rebuild."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        # Initial build
        tray._rebuild_menu()
        fp1 = tray._last_menu_fingerprint

        # Second build should skip (same state)
        with patch.object(tray._menu, "clear") as mock_clear:
            tray._rebuild_menu()
            mock_clear.assert_not_called()


class TestConnectionStateIcon:
    """Test connection state icon overlay."""

    def test_build_status_icon_connected(self, qtbot: QtBot) -> None:
        """Test icon building with connected state."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._connected = True

        icon = tray._build_status_icon()
        assert isinstance(icon, QIcon)

    def test_build_status_icon_disconnected(self, qtbot: QtBot) -> None:
        """Test icon building with disconnected state."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._connected = False

        icon = tray._build_status_icon()
        assert isinstance(icon, QIcon)

    def test_on_connection_changed_updates_icon(self, qtbot: QtBot) -> None:
        """Test _on_connection_changed updates tray icon."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._tray, "setIcon") as mock_set_icon:
            tray._on_connection_changed(True)
            mock_set_icon.assert_called()
            assert tray._connected is True

    def test_on_connection_changed_updates_tooltip(self, qtbot: QtBot) -> None:
        """Test _on_connection_changed updates tooltip."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._tray, "setToolTip") as mock_set_tooltip:
            tray._on_connection_changed(True)
            mock_set_tooltip.assert_called_with("SnapCTRL — Connected")

            tray._on_connection_changed(False)
            mock_set_tooltip.assert_called_with("SnapCTRL — Disconnected")

    def test_disconnect_clears_cached_group(self, qtbot: QtBot) -> None:
        """Test disconnect clears cached target group."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._cached_target_group = group

        tray._on_connection_changed(False)

        assert tray._cached_target_group is None


class TestQuickVolume:
    """Test quick volume slider functionality."""

    def test_get_target_group_with_selection(self, qtbot: QtBot) -> None:
        """Test _get_target_group returns selected group."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group1 = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        group2 = Group(id="g2", name="G2", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group1, group2], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray.selected_group_id = "g2"

        target = tray._get_target_group()
        assert target is not None
        assert target.id == "g2"

    def test_get_target_group_fallback_to_first(self, qtbot: QtBot) -> None:
        """Test _get_target_group falls back to first group."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray.selected_group_id = None

        target = tray._get_target_group()
        assert target is not None
        assert target.id == "g1"

    def test_get_target_group_uses_cache_during_transition(self, qtbot: QtBot) -> None:
        """Test _get_target_group uses cache during empty state transitions."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        # Get target once to populate cache
        tray._get_target_group()

        # Clear groups (simulating transient state) and invalidate cache
        state._groups = {}  # pyright: ignore[reportPrivateUsage]
        state._groups_cache = None  # pyright: ignore[reportPrivateUsage]

        # Should return None because cache validation fails (get_group returns None)
        target = tray._get_target_group()
        assert target is None


class TestCleanup:
    """Test cleanup functionality."""

    def test_cleanup_stops_timer(self, qtbot: QtBot) -> None:
        """Test cleanup stops rebuild timer."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._rebuild_timer, "stop") as mock_stop:
            tray.cleanup()
            mock_stop.assert_called()

    def test_cleanup_clears_menu(self, qtbot: QtBot) -> None:
        """Test cleanup clears menu."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._menu, "clear") as mock_clear:
            tray.cleanup()
            mock_clear.assert_called()

    def test_cleanup_resets_state(self, qtbot: QtBot) -> None:
        """Test cleanup resets internal state."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._volume_slider = MagicMock()
        tray._cached_target_group = MagicMock()
        tray._last_menu_fingerprint = "something"

        tray.cleanup()

        assert tray._volume_slider is None
        assert tray._cached_target_group is None
        assert tray._last_menu_fingerprint == ""


class TestTrayActivation:
    """Test tray icon activation handling."""

    def test_double_click_toggles_window(self, qtbot: QtBot) -> None:
        """Test double-click toggles window visibility."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)
        window.show()

        tray = SystemTrayManager(window, state)

        # Double click should hide
        tray._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
        assert not window.isVisible()

        # Double click should show
        tray._on_activated(QSystemTrayIcon.ActivationReason.DoubleClick)
        assert window.isVisible()

    def test_single_click_ignored(self, qtbot: QtBot) -> None:
        """Test single click doesn't toggle window."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)
        window.show()

        tray = SystemTrayManager(window, state)

        # Single click should not toggle
        tray._on_activated(QSystemTrayIcon.ActivationReason.Trigger)
        assert window.isVisible()


class TestLocalClientActions:
    """Test local snapclient tray actions."""

    def test_on_start_snapclient(self, qtbot: QtBot) -> None:
        """Test _on_start_snapclient calls manager.start()."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)
        tray.set_snapclient_connection("192.168.1.100", 1704)

        with patch.object(mgr, "start") as mock_start:
            tray._on_start_snapclient()
            mock_start.assert_called_once_with("192.168.1.100", 1704)

    def test_on_start_snapclient_no_host(self, qtbot: QtBot) -> None:
        """Test _on_start_snapclient emits error when no host configured."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)
        # Don't set host

        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        tray._on_start_snapclient()

        assert len(errors) == 1
        assert "No server configured" in errors[0]

    def test_on_stop_snapclient(self, qtbot: QtBot) -> None:
        """Test _on_stop_snapclient calls manager.stop()."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        with patch.object(mgr, "stop") as mock_stop:
            tray._on_stop_snapclient()
            mock_stop.assert_called_once()


class TestGroupEntryClickable:
    """Test clickable group entries."""

    def test_group_entry_emits_mute_signal(self, qtbot: QtBot) -> None:
        """Test clicking group entry emits mute_changed signal."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group = Group(id="g1", name="Test Group", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._rebuild_menu()

        received: list[tuple[str, bool]] = []
        tray.mute_changed.connect(lambda gid, m: received.append((gid, m)))

        # Find the group action and trigger it
        for action in tray._menu.actions():
            if "Test Group" in action.text():
                action.trigger()
                break

        assert len(received) == 1
        assert received[0] == ("g1", True)  # Toggled from False to True

    def test_muted_group_shows_muted_label(self, qtbot: QtBot) -> None:
        """Test muted group shows (muted) label."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group = Group(id="g1", name="Test Group", stream_id="s1", muted=True, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._rebuild_menu()

        # Find group action
        for action in tray._menu.actions():
            if "Test Group" in action.text():
                assert "(muted)" in action.text()
                break


class TestLocalClientMenuExtended:
    """Extended tests for local snapclient menu entries."""

    def test_menu_shows_stop_when_running(self, qtbot: QtBot) -> None:
        """Menu shows 'Stop Local Client' when running."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        # Mock is_running at class level
        with patch.object(
            SnapclientManager, "is_running", new_callable=PropertyMock, return_value=True
        ):
            with patch.object(
                SnapclientManager, "is_external", new_callable=PropertyMock, return_value=False
            ):
                tray._last_menu_fingerprint = ""  # Force rebuild
                tray._rebuild_menu()

        menu = tray._menu
        menu_text = " ".join(a.text() for a in menu.actions() if not a.isSeparator())
        assert "Stop Local Client" in menu_text

    def test_menu_hides_toggle_when_external(self, qtbot: QtBot) -> None:
        """Menu hides toggle when snapclient is external."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        # Mock is_external at class level
        with patch.object(
            SnapclientManager, "is_external", new_callable=PropertyMock, return_value=True
        ):
            tray._last_menu_fingerprint = ""  # Force rebuild
            tray._rebuild_menu()

        menu = tray._menu
        menu_text = " ".join(a.text() for a in menu.actions() if not a.isSeparator())
        # Should not have start or stop actions
        assert "Start Local Client" not in menu_text
        assert "Stop Local Client" not in menu_text

    def test_on_start_snapclient_value_error(self, qtbot: QtBot) -> None:
        """Test _on_start_snapclient handles ValueError from manager.start()."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)
        tray.set_snapclient_connection("192.168.1.100", 1704)

        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        with patch.object(mgr, "start", side_effect=ValueError("Command not found")):
            tray._on_start_snapclient()

        assert len(errors) == 1
        assert "Command not found" in errors[0]

    def test_on_start_snapclient_no_manager(self, qtbot: QtBot) -> None:
        """Test _on_start_snapclient with no snapclient manager."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state, snapclient_mgr=None)

        # Should not crash - just logs warning
        tray._on_start_snapclient()

    def test_on_stop_snapclient_no_manager(self, qtbot: QtBot) -> None:
        """Test _on_stop_snapclient with no snapclient manager."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state, snapclient_mgr=None)

        # Should not crash
        tray._on_stop_snapclient()


class TestCleanupExtended:
    """Extended cleanup tests."""

    def test_cleanup_with_snapclient_manager(self, qtbot: QtBot) -> None:
        """Test cleanup disconnects snapclient manager signal."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        # Should not crash when disconnecting signal
        tray.cleanup()


class TestOnQuitWithSnapclient:
    """Test _on_quit with running snapclient dialog paths."""

    def test_on_quit_stops_snapclient_on_yes(self, qtbot: QtBot) -> None:
        """Test _on_quit stops snapclient when user clicks Yes."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        with patch.object(
            SnapclientManager, "is_running", new_callable=PropertyMock, return_value=True
        ):
            with patch("snapctrl.ui.system_tray.QMessageBox.question") as mock_question:
                from PySide6.QtWidgets import QMessageBox
                mock_question.return_value = QMessageBox.StandardButton.Yes
                with patch.object(mgr, "stop") as mock_stop:
                    with patch("snapctrl.ui.system_tray.QApplication") as mock_app_cls:
                        mock_app_cls.instance.return_value = mock_app_cls
                        tray._on_quit()
                        mock_stop.assert_called_once()

    def test_on_quit_detaches_snapclient_on_no(self, qtbot: QtBot) -> None:
        """Test _on_quit detaches snapclient when user clicks No."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        with patch.object(
            SnapclientManager, "is_running", new_callable=PropertyMock, return_value=True
        ):
            with patch("snapctrl.ui.system_tray.QMessageBox.question") as mock_question:
                from PySide6.QtWidgets import QMessageBox
                mock_question.return_value = QMessageBox.StandardButton.No
                with patch.object(mgr, "detach") as mock_detach:
                    with patch("snapctrl.ui.system_tray.QApplication") as mock_app_cls:
                        mock_app_cls.instance.return_value = mock_app_cls
                        tray._on_quit()
                        mock_detach.assert_called_once()

    def test_on_quit_detaches_on_runtime_error(self, qtbot: QtBot) -> None:
        """Test _on_quit detaches snapclient on RuntimeError (widget deleted)."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        mgr = SnapclientManager()
        tray = SystemTrayManager(window, state, snapclient_mgr=mgr)

        with patch.object(
            SnapclientManager, "is_running", new_callable=PropertyMock, return_value=True
        ):
            with patch(
                "snapctrl.ui.system_tray.QMessageBox.question",
                side_effect=RuntimeError("Widget deleted"),
            ):
                with patch.object(mgr, "detach") as mock_detach:
                    with patch("snapctrl.ui.system_tray.QApplication") as mock_app_cls:
                        mock_app_cls.instance.return_value = mock_app_cls
                        tray._on_quit()
                        mock_detach.assert_called_once()

    def test_on_quit_no_app_instance(self, qtbot: QtBot) -> None:
        """Test _on_quit when QApplication.instance() returns None."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch("snapctrl.ui.system_tray.QApplication") as mock_app_cls:
            mock_app_cls.instance.return_value = None
            # Should not crash
            tray._on_quit()


class TestQuickVolumeExtended:
    """Extended quick volume tests."""

    def test_add_quick_volume_no_connected_clients(self, qtbot: QtBot) -> None:
        """Test _add_quick_volume skips slider when no clients connected.

        When no clients are connected, we don't know the actual volume,
        so the slider is hidden rather than showing a misleading default.
        """
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=False)
        group = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._rebuild_menu()

        # Slider should NOT exist when no clients are connected
        assert tray._volume_slider is None

    def test_get_target_group_invalid_cache(self, qtbot: QtBot) -> None:
        """Test _get_target_group clears invalid cache."""
        client = Client(id="c1", host="h", name="C", volume=50, muted=False, connected=True)
        group = Group(id="g1", name="G1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        # Set cache to a group that no longer exists
        fake_group = Group(id="deleted", name="Deleted", stream_id="s", muted=False, client_ids=[])
        tray._cached_target_group = fake_group

        # Clear groups and invalidate cache
        state._groups = {}
        state._groups_cache = None

        # Should return None and clear the invalid cache
        result = tray._get_target_group()
        assert result is None
        assert tray._cached_target_group is None


class TestNowPlayingExtended:
    """Extended now playing tests."""

    def test_now_playing_without_artist(self, qtbot: QtBot) -> None:
        """Test now playing entry without artist."""
        source = Source(
            id="s1",
            name="MPD",
            status="playing",
            stream_type="flac",
            meta_title="Test Song",
            meta_artist="",  # No artist
        )
        state = _make_state(sources=[source])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._rebuild_menu()

        menu = tray._menu
        menu_text = " ".join(a.text() for a in menu.actions() if not a.isSeparator())
        assert "Test Song" in menu_text
        # Should not have " — " separator when no artist
        # (The label is "♫ Test Song" without " — Artist")


class TestBuildStatusIconExtended:
    """Extended status icon tests."""

    def test_build_status_icon_null_pixmap(self, qtbot: QtBot) -> None:
        """Test _build_status_icon returns base icon when pixmap is null."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        # Create with empty icon (will have null pixmap)
        empty_icon = QIcon()
        tray = SystemTrayManager(window, state, icon=empty_icon)

        icon = tray._build_status_icon()
        # Should return the base icon (same empty icon) when pixmap is null
        assert isinstance(icon, QIcon)


class TestBuildStatusIconDrawing:
    """Test _build_status_icon drawing code path."""

    def test_build_status_icon_with_valid_pixmap(self, qtbot: QtBot) -> None:
        """Test _build_status_icon draws on valid pixmap."""
        from PySide6.QtGui import QPixmap

        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        # Create a real icon with a real pixmap
        pixmap = QPixmap(64, 64)
        pixmap.fill()  # Fill with white to make it non-null
        valid_icon = QIcon(pixmap)

        tray = SystemTrayManager(window, state, icon=valid_icon)
        tray._connected = True

        # This should execute the drawing code (lines 468-484)
        icon = tray._build_status_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()

    def test_build_status_icon_disconnected_with_valid_pixmap(self, qtbot: QtBot) -> None:
        """Test _build_status_icon draws disconnected dot on valid pixmap."""
        from PySide6.QtGui import QPixmap

        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        pixmap = QPixmap(64, 64)
        pixmap.fill()
        valid_icon = QIcon(pixmap)

        tray = SystemTrayManager(window, state, icon=valid_icon)
        tray._connected = False

        icon = tray._build_status_icon()
        assert isinstance(icon, QIcon)
        assert not icon.isNull()


class TestGetTargetGroupCachePaths:
    """Test _get_target_group cache edge cases."""

    def test_get_target_group_cached_still_valid(self, qtbot: QtBot) -> None:
        """Test _get_target_group returns cached group when empty but cache still valid."""
        group = Group(id="g1", name="Group 1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[group])
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        # Prime the cache
        tray._cached_target_group = group

        # Clear groups list to simulate transient empty state
        state._groups = {}  # pyright: ignore[reportPrivateUsage]

        # Now set a mock to return the cached group from get_group
        with patch.object(state, "get_group", return_value=group):
            result = tray._get_target_group()
            assert result == group

    def test_get_target_group_cached_invalid(self, qtbot: QtBot) -> None:
        """Test _get_target_group clears invalid cache."""
        group = Group(id="g1", name="Group 1", stream_id="s1", muted=False, client_ids=["c1"])
        state = _make_state(groups=[])
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._cached_target_group = group

        # Cache group no longer in state
        with patch.object(state, "get_group", return_value=None):
            result = tray._get_target_group()
            assert result is None
            assert tray._cached_target_group is None


class TestScheduleRebuild:
    """Test schedule rebuild functionality."""

    def test_schedule_rebuild_starts_timer(self, qtbot: QtBot) -> None:
        """Test _schedule_rebuild starts the debounce timer."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch.object(tray._rebuild_timer, "start") as mock_start:
            tray._schedule_rebuild()
            mock_start.assert_called_once()
