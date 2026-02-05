"""Tests for UI widgets."""

from unittest.mock import MagicMock, patch

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import QMenu
from pytestqt.qtbot import QtBot

from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source
from snapctrl.ui.widgets.group_card import GroupCard
from snapctrl.ui.widgets.volume_slider import VolumeSlider


class TestVolumeSlider:
    """Test VolumeSlider widget."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that slider can be created."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)
        assert slider.volume == 50
        assert not slider.is_muted

    def test_set_volume(self, qtbot: QtBot) -> None:
        """Test setting volume."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)
        slider.set_volume(75)
        assert slider.volume == 75
        assert slider._volume_label.text() == "75%"

    def test_mute_toggle(self, qtbot: QtBot) -> None:
        """Test mute toggle."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        assert not slider.is_muted

        slider.set_muted(True)
        assert slider.is_muted
        assert slider._mute_button.text() == "🔇"

        slider.set_muted(False)
        assert not slider.is_muted
        assert slider._mute_button.text() == "🔊"

    def test_mute_changes_volume_label(self, qtbot: QtBot) -> None:
        """Test that mute changes volume label."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_muted(True)
        assert slider._volume_label.text() == "M"

        slider.set_muted(False)
        assert slider._volume_label.text() == "50%"

    def test_set_volume_and_mute(self, qtbot: QtBot) -> None:
        """Test atomic volume and mute set."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume_and_mute(30, True)
        assert slider.volume == 0
        assert slider.is_muted

        slider.set_volume_and_mute(30, False)
        assert slider.volume == 30
        assert not slider.is_muted


class TestGroupCard:
    """Test GroupCard widget."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that card can be created."""
        card = GroupCard()
        qtbot.addWidget(card)
        assert card._name_label.text() == "Group Name"

    def test_with_group(self, qtbot: QtBot) -> None:
        """Test card with group data."""
        group = Group(
            id="g1",
            name="Living Room",
            stream_id="mpd",
            muted=False,
            client_ids=["c1"],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        assert card._name_label.text() == "Living Room"
        assert not card._volume_slider.is_muted  # pyright: ignore[reportPrivateUsage]

    def test_with_muted_group(self, qtbot: QtBot) -> None:
        """Test card with muted group."""
        group = Group(
            id="g1",
            name="Muted Room",
            stream_id="mpd",
            muted=True,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        assert card._volume_slider.is_muted  # pyright: ignore[reportPrivateUsage]

    def test_set_sources(self, qtbot: QtBot) -> None:
        """Test setting sources."""
        card = GroupCard()
        qtbot.addWidget(card)

        sources = [
            Source(id="s1", name="MPD", status="playing", stream_type="flac"),
            Source(id="s2", name="Spotify", status="idle", stream_type="ogg"),
        ]
        card.set_sources(sources)

        assert card._source_combo.count() == 2
        assert card._source_combo.itemText(0) == "MPD"

    def test_expand_toggle(self, qtbot: QtBot) -> None:
        """Test expand/collapse functionality."""
        card = GroupCard()
        qtbot.addWidget(card)
        card.show()  # Widget must be shown for isVisible() to work

        assert not card._expanded
        assert card._client_list.isHidden()

        card._toggle_expand()
        assert card._expanded
        assert not card._client_list.isHidden()
        assert card._expand_button.text() == "▲"

        card._toggle_expand()
        assert not card._expanded
        assert card._client_list.isHidden()
        assert card._expand_button.text() == "▼"

    def test_add_client(self, qtbot: QtBot) -> None:
        """Test adding client to the list."""
        card = GroupCard()
        qtbot.addWidget(card)

        # Expand to show client list
        card._toggle_expand()

        card.add_client(client_id="c1", client_name="Player One", client_volume=65)
        assert "c1" in card._client_cards
        assert "Player One" in card._client_cards["c1"].name

    def test_signals_exist(self, qtbot: QtBot) -> None:
        """Test that card has all required signals."""
        card = GroupCard()
        qtbot.addWidget(card)

        # Check signals exist
        assert hasattr(card, "volume_changed")
        assert hasattr(card, "mute_toggled")
        assert hasattr(card, "source_changed")
        assert hasattr(card, "expand_toggled")
        assert hasattr(card, "client_volume_changed")
        assert hasattr(card, "client_mute_toggled")


class TestGroupCardSelection:
    """Test GroupCard selection state."""

    def test_set_selected(self, qtbot: QtBot) -> None:
        """Test setting selection state."""
        card = GroupCard()
        qtbot.addWidget(card)

        assert card._selected is False

        card.set_selected(True)
        assert card._selected is True

        card.set_selected(False)
        assert card._selected is False

    def test_clicked_signal(self, qtbot: QtBot) -> None:
        """Test clicked signal emission on mouse press."""
        card = GroupCard()
        qtbot.addWidget(card)

        received: list[bool] = []
        card.clicked.connect(lambda: received.append(True))

        # Create a proper mouse event
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(10, 10),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )
        card.mousePressEvent(event)

        # Should have emitted
        assert received == [True]


class TestGroupCardSourceChange:
    """Test GroupCard source change handling."""

    def test_source_changed_signal(self, qtbot: QtBot) -> None:
        """Test source changed signal emission."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        sources = [
            Source(id="s1", name="MPD", status="playing", stream_type="flac"),
            Source(id="s2", name="Spotify", status="idle", stream_type="ogg"),
        ]
        card.set_sources(sources)

        received: list[tuple[str, str]] = []
        card.source_changed.connect(lambda gid, sid: received.append((gid, sid)))

        # Manually trigger source change handler
        card._source_combo.setCurrentIndex(1)  # Select Spotify

        # Source changed signal should be emitted
        assert len(received) == 1
        assert received[0] == ("g1", "s2")


class TestGroupCardExpand:
    """Test GroupCard expand functionality."""

    def test_expand_toggled_signal(self, qtbot: QtBot) -> None:
        """Test expand toggled signal emission."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        received: list[tuple[str, bool]] = []
        card.expand_toggled.connect(lambda gid, exp: received.append((gid, exp)))

        card._toggle_expand()

        assert len(received) == 1
        assert received[0] == ("g1", True)

    def test_set_expanded(self, qtbot: QtBot) -> None:
        """Test set_expanded method."""
        card = GroupCard()
        qtbot.addWidget(card)
        card.show()

        assert card.is_expanded is False

        card.set_expanded(True)
        assert card.is_expanded is True
        assert card._expand_button.text() == "▲"

        card.set_expanded(False)
        assert card.is_expanded is False
        assert card._expand_button.text() == "▼"


class TestGroupCardVolume:
    """Test GroupCard volume handling."""

    def test_set_volume(self, qtbot: QtBot) -> None:
        """Test setting volume."""
        card = GroupCard()
        qtbot.addWidget(card)

        card.set_volume(80)
        assert card._volume_slider.volume == 80

    def test_volume_changed_signal(self, qtbot: QtBot) -> None:
        """Test volume changed signal emission."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        received: list[tuple[str, int]] = []
        card.volume_changed.connect(lambda gid, vol: received.append((gid, vol)))

        # Trigger volume change through internal handler
        card._on_volume_slider_changed(75)

        assert len(received) == 1
        assert received[0] == ("g1", 75)

    def test_mute_toggled_signal(self, qtbot: QtBot) -> None:
        """Test mute toggled signal emission."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        received: list[tuple[str, bool]] = []
        card.mute_toggled.connect(lambda gid, muted: received.append((gid, muted)))

        # Trigger mute through internal handler
        card._on_slider_mute_toggled(True)

        assert len(received) == 1
        assert received[0] == ("g1", True)


class TestGroupCardUpdateFromState:
    """Test GroupCard update_from_state method."""

    def test_update_from_state_basic(self, qtbot: QtBot) -> None:
        """Test basic update_from_state."""
        group = Group(
            id="g1",
            name="Old Name",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        new_group = Group(
            id="g1",
            name="New Name",
            stream_id="s2",
            muted=True,
            client_ids=[],
        )
        sources = [
            Source(id="s1", name="MPD", status="playing", stream_type="flac"),
            Source(id="s2", name="Spotify", status="idle", stream_type="ogg"),
        ]

        card.update_from_state(new_group, sources)

        assert card._name_label.text() == "New Name"
        assert card._volume_slider.is_muted is True

    def test_update_from_state_with_clients(self, qtbot: QtBot) -> None:
        """Test update_from_state with clients."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=["c1", "c2"],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        clients = [
            Client(id="c1", host="h1", name="Player 1", volume=50, connected=True),
            Client(id="c2", host="h2", name="Player 2", volume=70, connected=True),
        ]
        sources = [
            Source(id="s1", name="MPD", status="playing", stream_type="flac"),
        ]

        card.update_from_state(group, sources, clients)

        # Should have created client cards
        assert "c1" in card._client_cards
        assert "c2" in card._client_cards


class TestGroupCardEventFilter:
    """Test GroupCard event filter."""

    def test_event_filter_name_label_click(self, qtbot: QtBot) -> None:
        """Test event filter handles clicks on name label."""
        card = GroupCard()
        qtbot.addWidget(card)

        received: list[bool] = []
        card.clicked.connect(lambda: received.append(True))

        # Create mouse press event
        event = QMouseEvent(
            QEvent.Type.MouseButtonPress,
            QPointF(0, 0),
            Qt.MouseButton.LeftButton,
            Qt.MouseButton.LeftButton,
            Qt.KeyboardModifier.NoModifier,
        )

        # Send event to name label through filter
        result = card.eventFilter(card._name_label, event)

        assert result is True
        assert received == [True]


class TestGroupCardRefreshTheme:
    """Test GroupCard theme refresh."""

    def test_refresh_theme(self, qtbot: QtBot) -> None:
        """Test refresh_theme doesn't crash."""
        card = GroupCard()
        qtbot.addWidget(card)

        card.refresh_theme()  # Should not crash


class TestGroupCardSetGroup:
    """Test GroupCard set_group method."""

    def test_set_group(self, qtbot: QtBot) -> None:
        """Test set_group method."""
        card = GroupCard()
        qtbot.addWidget(card)

        group = Group(
            id="g1",
            name="Living Room",
            stream_id="s1",
            muted=True,
            client_ids=[],
        )
        card.set_group(group)

        assert card._name_label.text() == "Living Room"
        assert card._volume_slider.is_muted is True


class TestGroupCardContextMenu:
    """Test group card context menu."""

    def test_context_menu_rename_confirmed(self, qtbot: QtBot) -> None:
        """Test context menu rename action when confirmed."""
        group = Group(
            id="g1",
            name="Old Name",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda gid, name: received.append((gid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.group_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("New Name", True),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        assert received == [("g1", "New Name")]

    def test_context_menu_rename_cancelled(self, qtbot: QtBot) -> None:
        """Test context menu rename action when cancelled."""
        group = Group(
            id="g1",
            name="Old Name",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda gid, name: received.append((gid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.group_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("", False),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        assert received == []

    def test_context_menu_no_group(self, qtbot: QtBot) -> None:
        """Test context menu when no group is set."""
        card = GroupCard()  # No group
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda gid, name: received.append((gid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action  # User selected rename but no group

        with patch("snapctrl.ui.widgets.group_card.QMenu", return_value=mock_menu):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        # No signal when group is None
        assert received == []

    def test_context_menu_same_name(self, qtbot: QtBot) -> None:
        """Test context menu doesn't emit when name unchanged."""
        group = Group(
            id="g1",
            name="Same Name",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda gid, name: received.append((gid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.group_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("Same Name", True),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        assert received == []

    def test_context_menu_whitespace_name(self, qtbot: QtBot) -> None:
        """Test context menu handles whitespace-only name."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda gid, name: received.append((gid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = mock_rename_action

        with (
            patch("snapctrl.ui.widgets.group_card.QMenu", return_value=mock_menu),
            patch(
                "snapctrl.ui.widgets.dialogs.StyledInputDialog.get_text",
                return_value=("   ", True),
            ),
        ):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        # Empty after strip, should not emit
        assert received == []

    def test_context_menu_no_action_selected(self, qtbot: QtBot) -> None:
        """Test context menu when dismissed without selection."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)
        card.show()

        received: list[tuple[str, str]] = []
        card.rename_requested.connect(lambda gid, name: received.append((gid, name)))

        mock_menu = MagicMock(spec=QMenu)
        mock_rename_action = MagicMock()
        mock_menu.addAction.return_value = mock_rename_action
        mock_menu.exec.return_value = None  # Menu dismissed

        with patch("snapctrl.ui.widgets.group_card.QMenu", return_value=mock_menu):
            event = QContextMenuEvent(
                QContextMenuEvent.Reason.Mouse, QPoint(10, 10), QPoint(100, 100)
            )
            card.contextMenuEvent(event)

        assert received == []


class TestGroupCardClearClients:
    """Test GroupCard clearing existing clients."""

    def test_update_clients_clears_old(self, qtbot: QtBot) -> None:
        """Test that _update_clients clears old client cards."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=["c1"],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        # Add initial clients
        clients1 = [Client(id="c1", host="h", name="C1", volume=50, connected=True)]
        card.update_clients(clients1)
        assert "c1" in card._client_cards

        # Update with different clients
        clients2 = [Client(id="c2", host="h", name="C2", volume=60, connected=True)]
        card.update_clients(clients2)

        # Old client should be removed
        assert "c1" not in card._client_cards
        assert "c2" in card._client_cards


class TestGroupCardVolumeEdgeCases:
    """Test GroupCard volume calculation edge cases."""

    def test_volume_no_connected_clients(self, qtbot: QtBot) -> None:
        """Test volume when no clients are connected."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=["c1"],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        # All clients disconnected
        clients = [
            Client(id="c1", host="h", name="C1", volume=80, connected=False),
            Client(id="c2", host="h", name="C2", volume=60, connected=False),
        ]
        card._update_group_volume_from_clients(clients)

        # Should use average of all clients
        assert card._volume_slider.volume == 70

    def test_volume_no_clients(self, qtbot: QtBot) -> None:
        """Test volume when no clients exist."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=[],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        # No clients at all
        card._update_group_volume_from_clients([])

        # Should default to 50
        assert card._volume_slider.volume == 50


class TestGroupCardRefreshThemeWithClients:
    """Test GroupCard refresh_theme with client cards."""

    def test_refresh_theme_refreshes_clients(self, qtbot: QtBot) -> None:
        """Test refresh_theme also refreshes client cards."""
        group = Group(
            id="g1",
            name="Test",
            stream_id="s1",
            muted=False,
            client_ids=["c1"],
        )
        card = GroupCard(group)
        qtbot.addWidget(card)

        # Add a client
        clients = [Client(id="c1", host="h", name="C1", volume=50, connected=True)]
        card.update_clients(clients)

        # Mock the client card's refresh_theme
        mock_client_card = MagicMock()
        card._client_cards["c1"] = mock_client_card

        card.refresh_theme()

        # Client card's refresh_theme should have been called
        mock_client_card.refresh_theme.assert_called_once()


class TestGroupCardUpdateFromGroupNoGroup:
    """Test GroupCard _update_from_group when no group is set."""

    def test_update_from_group_no_group(self, qtbot: QtBot) -> None:
        """Test _update_from_group returns early when no group."""
        card = GroupCard()  # No group
        qtbot.addWidget(card)

        original_text = card._name_label.text()

        card._update_from_group()

        # Should not crash, label unchanged
        assert card._name_label.text() == original_text
