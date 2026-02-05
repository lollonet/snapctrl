"""Tests for ClientCard widget."""

from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QLabel, QMenu
from pytestqt.qtbot import QtBot

from snapctrl.models.client import Client
from snapctrl.ui.widgets.client_card import ClientCard


class TestClientCard:
    """Test ClientCard widget."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that client card can be created."""
        card = ClientCard(
            client_id="c1",
            name="Living Room",
            volume=50,
            muted=False,
            connected=True,
        )
        qtbot.addWidget(card)
        card.show()

        assert card.client_id == "c1"
        assert card.name == "Living Room"

    def test_mute_toggle(self, qtbot: QtBot) -> None:
        """Test mute toggle."""
        card = ClientCard(
            client_id="c1",
            name="Test",
            volume=50,
            muted=False,
        )
        qtbot.addWidget(card)
        card.show()

        assert not card._volume_slider.is_muted

        card.set_muted(True)
        assert card._volume_slider.is_muted

        card.set_muted(False)
        assert not card._volume_slider.is_muted

    def test_connected_status(self, qtbot: QtBot) -> None:
        """Test connection status display."""
        card = ClientCard(
            client_id="c1",
            name="Test",
            connected=True,
        )
        qtbot.addWidget(card)
        card.show()

        # Connected: filled circle with green color
        assert "●" in card._status_indicator.text()
        assert "#4CAF50" in card._status_indicator.styleSheet()  # Green

        # Disconnected: filled circle with red color
        card.set_connected(False)
        assert "●" in card._status_indicator.text()
        assert "#F44336" in card._status_indicator.styleSheet()  # Red

    def test_update_from_client(self, qtbot: QtBot) -> None:
        """Test updating from Client model."""
        card = ClientCard(
            client_id="c1",
            name="Old Name",
            volume=50,
        )
        qtbot.addWidget(card)
        card.show()

        client = Client(
            id="c1",
            host="192.168.1.10",
            name="New Name",
            volume=75,
            muted=True,
            connected=False,
        )

        card.update_from_client(client)

        assert card.name == "New Name"
        # When muted, slider value is 0 (stored volume is in _volume_before_mute)
        assert card._volume_slider.volume == 0
        assert card._volume_slider.is_muted
        # Disconnected: filled circle with red color
        assert "●" in card._status_indicator.text()
        assert "#F44336" in card._status_indicator.styleSheet()  # Red

    def test_update_from_client_not_muted(self, qtbot: QtBot) -> None:
        """Test updating from Client model when not muted."""
        card = ClientCard(
            client_id="c1",
            name="Old Name",
            volume=50,
            muted=True,
        )
        qtbot.addWidget(card)
        card.show()

        # Initially muted - slider should be 0
        assert card._volume_slider.volume == 0

        client = Client(
            id="c1",
            host="192.168.1.10",
            name="New Name",
            volume=75,
            muted=False,
            connected=True,
        )

        card.update_from_client(client)

        assert card.name == "New Name"
        # When not muted, slider should show actual volume
        assert card._volume_slider.volume == 75
        assert not card._volume_slider.is_muted
        assert "●" in card._status_indicator.text()

    def test_signals_exist(self, qtbot: QtBot) -> None:
        """Test that card has all required signals."""
        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        # Check signals exist
        assert hasattr(card, "volume_changed")
        assert hasattr(card, "mute_toggled")
        assert hasattr(card, "rename_requested")

    def test_rename_signal_emits(self, qtbot: QtBot) -> None:
        """Test that rename_requested signal can be emitted."""
        card = ClientCard(client_id="c1", name="Old Name")
        qtbot.addWidget(card)

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda cid, name: received.append((cid, name)))

        card.rename_requested.emit("c1", "New Name")

        assert received == [("c1", "New Name")]


class TestClientCardVolumeSignals:
    """Test volume change signal propagation."""

    def test_volume_changed_signal(self, qtbot: QtBot) -> None:
        """Test volume change emits signal with client ID."""
        card = ClientCard(client_id="c1", name="Test", volume=50)
        qtbot.addWidget(card)

        received: list[tuple[str, int]] = []
        card.volume_changed.connect(lambda cid, vol: received.append((cid, vol)))

        # Trigger volume change through internal handler
        card._on_volume_changed(75)

        assert received == [("c1", 75)]

    def test_mute_toggled_signal(self, qtbot: QtBot) -> None:
        """Test mute toggle emits signal with client ID."""
        card = ClientCard(client_id="c1", name="Test", muted=False)
        qtbot.addWidget(card)

        received: list[tuple[str, bool]] = []
        card.mute_toggled.connect(lambda cid, muted: received.append((cid, muted)))

        # Trigger mute through internal handler
        card._on_mute_toggled(True)

        assert received == [("c1", True)]


class TestClientCardSelection:
    """Test client card selection state."""

    def test_set_selected(self, qtbot: QtBot) -> None:
        """Test setting selection state."""
        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        assert card._selected is False

        card.set_selected(True)
        assert card._selected is True
        assert "border: 2px" in card.styleSheet()

        card.set_selected(False)
        assert card._selected is False


class TestClientCardClicked:
    """Test client card click handling."""

    def test_clicked_signal(self, qtbot: QtBot) -> None:
        """Test clicked signal is emitted."""
        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        received: list[str] = []
        card.clicked.connect(received.append)

        # Simulate click via event filter

        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card.eventFilter(card._name_label, event)

        assert received == ["c1"]


class TestClientCardRefreshTheme:
    """Test client card theme refresh."""

    def test_refresh_theme(self, qtbot: QtBot) -> None:
        """Test refresh_theme doesn't crash."""
        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        card.refresh_theme()  # Should not crash

    def test_refresh_theme_disconnected(self, qtbot: QtBot) -> None:
        """Test refresh_theme with disconnected state."""
        card = ClientCard(client_id="c1", name="Test", connected=False)
        qtbot.addWidget(card)

        card.refresh_theme()
        # Status indicator should have error color
        assert "F44336" in card._status_indicator.styleSheet()


class TestClientCardDisconnectedInit:
    """Test client card with disconnected state at init."""

    def test_disconnected_at_init(self, qtbot: QtBot) -> None:
        """Test card created with disconnected state."""
        card = ClientCard(
            client_id="c1",
            name="Test",
            connected=False,
        )
        qtbot.addWidget(card)

        assert card._connected is False
        assert "F44336" in card._status_indicator.styleSheet()
        assert card._status_indicator.toolTip() == "Disconnected"


class TestClientCardMousePress:
    """Test client card mouse press handling."""

    def test_mouse_press_emits_clicked(self, qtbot: QtBot) -> None:
        """Test mouse press emits clicked signal."""

        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        received: list[str] = []
        card.clicked.connect(received.append)

        # Create mouse event
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card.mousePressEvent(event)

        assert received == ["c1"]


class TestClientCardEventFilterMultiple:
    """Test client card event filter for multiple widgets."""

    def test_event_filter_status_indicator_click(self, qtbot: QtBot) -> None:
        """Test event filter handles clicks on status indicator."""

        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        received: list[str] = []
        card.clicked.connect(received.append)

        # Create mouse press event
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Send event to status indicator through filter
        result = card.eventFilter(card._status_indicator, event)

        assert result is True
        assert received == ["c1"]

    def test_event_filter_other_widget(self, qtbot: QtBot) -> None:
        """Test event filter ignores clicks on other widgets."""

        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)

        received: list[str] = []
        card.clicked.connect(received.append)

        # Create a different widget
        other_widget = QLabel("Other")

        # Create mouse press event
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Send event to other widget through filter
        result = card.eventFilter(other_widget, event)

        assert result is False
        assert received == []


class TestClientCardName:
    """Test client card name property."""

    def test_name_property(self, qtbot: QtBot) -> None:
        """Test name property returns correct value."""
        card = ClientCard(client_id="c1", name="Test Name")
        qtbot.addWidget(card)

        assert card.name == "Test Name"


class TestClientCardContextMenu:
    """Test client card context menu."""

    def test_context_menu_rename_confirmed(self, qtbot: QtBot) -> None:
        """Test context menu rename action when confirmed."""

        card = ClientCard(client_id="c1", name="Old Name")
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda cid, name: received.append((cid, name)))

        # Create a mock menu that returns the rename action when exec is called
        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action  # User selected rename

        with (
            patch("snapctrl.ui.widgets.client_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("New Name", True),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        assert received == [("c1", "New Name")]

    def test_context_menu_rename_cancelled(self, qtbot: QtBot) -> None:
        """Test context menu rename action when cancelled."""

        card = ClientCard(client_id="c1", name="Old Name")
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda cid, name: received.append((cid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.client_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("", False),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        # Signal should not be emitted when cancelled
        assert received == []

    def test_context_menu_rename_same_name(self, qtbot: QtBot) -> None:
        """Test context menu doesn't emit when name unchanged."""

        card = ClientCard(client_id="c1", name="Same Name")
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda cid, name: received.append((cid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.client_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("Same Name", True),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        # Signal should not be emitted when name unchanged
        assert received == []

    def test_context_menu_no_action_selected(self, qtbot: QtBot) -> None:
        """Test context menu when no action is selected."""

        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda cid, name: received.append((cid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = None  # Menu dismissed without selection

        with patch("snapctrl.ui.widgets.client_card.QMenu", return_value=mock_menu):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        assert received == []

    def test_context_menu_whitespace_name(self, qtbot: QtBot) -> None:
        """Test context menu handles whitespace-only new name."""

        card = ClientCard(client_id="c1", name="Test")
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda cid, name: received.append((cid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.client_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("   ", True),  # Whitespace only
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        # Empty after strip, no signal
        assert received == []
