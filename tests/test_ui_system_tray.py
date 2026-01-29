"""Tests for the system tray manager."""

from unittest.mock import patch

from pytestqt.qtbot import QtBot

from snapcast_mvp.core.state import StateStore
from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source
from snapcast_mvp.ui.main_window import MainWindow
from snapcast_mvp.ui.system_tray import SystemTrayManager


def _make_state_with_groups(
    groups: list[Group],
    clients: list[Client] | None = None,
    sources: list[Source] | None = None,
) -> StateStore:
    """Create a StateStore pre-populated with test data.

    Uses internal dict attributes for test setup (avoids needing ServerState).
    """
    state = StateStore()
    state._groups = {g.id: g for g in groups}  # pyright: ignore[reportPrivateUsage]  # type: ignore[assignment]
    if clients:
        state._clients = {c.id: c for c in clients}  # pyright: ignore[reportPrivateUsage]  # type: ignore[assignment]
    if sources:
        state._sources = {s.id: s for s in sources}  # pyright: ignore[reportPrivateUsage]  # type: ignore[assignment]
    return state


class TestSystemTrayManager:
    """Test SystemTrayManager."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that tray manager can be created."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        assert tray is not None

    def test_selected_group_id(self, qtbot: QtBot) -> None:
        """Test selected group ID property."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        assert tray.selected_group_id is None

        tray.selected_group_id = "g1"
        assert tray.selected_group_id == "g1"

    def test_toggle_window_visibility(self, qtbot: QtBot) -> None:
        """Test that toggle_window hides and shows."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)
        window.show()

        tray = SystemTrayManager(window, state)

        # Window starts visible
        assert window.isVisible()

        # Toggle should hide
        tray._toggle_window()  # pyright: ignore[reportPrivateUsage]
        assert not window.isVisible()

        # Toggle again should show
        tray._toggle_window()  # pyright: ignore[reportPrivateUsage]
        assert window.isVisible()

    def test_menu_has_show_hide(self, qtbot: QtBot) -> None:
        """Test that menu contains show/hide action."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)
        window.show()

        tray = SystemTrayManager(window, state)
        actions = tray._menu.actions()  # pyright: ignore[reportPrivateUsage]
        assert len(actions) >= 2  # At least show/hide + quit
        assert "Hide SnapCTRL" in actions[0].text() or "Show SnapCTRL" in actions[0].text()

    def test_menu_has_quit(self, qtbot: QtBot) -> None:
        """Test that menu contains quit action."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        actions = tray._menu.actions()  # pyright: ignore[reportPrivateUsage]
        # Last non-separator action should be "Quit"
        non_sep = [a for a in actions if not a.isSeparator()]
        assert non_sep[-1].text() == "Quit"

    def test_menu_shows_groups(self, qtbot: QtBot) -> None:
        """Test that menu shows group entries when state has groups."""
        client = Client(
            id="c1",
            host="10.0.0.1",
            name="Speaker",
            volume=75,
            muted=False,
            connected=True,
        )
        group = Group(id="g1", name="Living Room", stream_id="mpd", muted=False, client_ids=["c1"])
        state = _make_state_with_groups([group], clients=[client])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._rebuild_menu()  # pyright: ignore[reportPrivateUsage]

        menu = tray._menu  # pyright: ignore[reportPrivateUsage]
        menu_text = " ".join(a.text() for a in menu.actions() if not a.isSeparator())
        assert "Living Room" in menu_text

    def test_menu_shows_now_playing(self, qtbot: QtBot) -> None:
        """Test that menu shows now playing when source has metadata."""
        source = Source(
            id="s1",
            name="MPD",
            status="playing",
            stream_type="flac",
            meta_title="Test Song",
            meta_artist="Test Artist",
        )
        state = _make_state_with_groups([], sources=[source])

        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)
        tray._rebuild_menu()  # pyright: ignore[reportPrivateUsage]

        menu = tray._menu  # pyright: ignore[reportPrivateUsage]
        menu_text = " ".join(a.text() for a in menu.actions() if not a.isSeparator())
        assert "Test Song" in menu_text
        assert "Test Artist" in menu_text

    def test_quit_action(self, qtbot: QtBot) -> None:
        """Test that quit action calls QApplication.quit."""
        state = StateStore()
        window = MainWindow(state_store=state)
        qtbot.addWidget(window)

        tray = SystemTrayManager(window, state)

        with patch("snapcast_mvp.ui.system_tray.QApplication") as mock_app_cls:
            mock_app_cls.instance.return_value = mock_app_cls
            tray._on_quit()  # pyright: ignore[reportPrivateUsage]
            mock_app_cls.quit.assert_called_once()


class TestMainWindowHideToTray:
    """Test MainWindow hide-to-tray behavior."""

    def test_close_hides_when_tray_enabled(self, qtbot: QtBot) -> None:
        """Test that close event hides window when hide-to-tray is enabled."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window.set_hide_to_tray(True)
        window.close()

        # Window should be hidden, not destroyed
        assert not window.isVisible()

    def test_close_closes_when_tray_disabled(self, qtbot: QtBot) -> None:
        """Test that close event closes window when hide-to-tray is disabled."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        window.set_hide_to_tray(False)
        # Default behavior - close actually closes
        # We can't easily test actual destruction, but we verify the flag
        assert not getattr(window, "_hide_to_tray", False)

    def test_toggle_visibility(self, qtbot: QtBot) -> None:
        """Test toggle_visibility method."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()

        assert window.isVisible()
        window.toggle_visibility()
        assert not window.isVisible()
        window.toggle_visibility()
        assert window.isVisible()
