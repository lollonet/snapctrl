"""Tests for ClientCard widget."""

from pytestqt.qtbot import QtBot

from snapcast_mvp.models.client import Client
from snapcast_mvp.ui.widgets.client_card import ClientCard


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
