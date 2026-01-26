"""Tests for UI widgets."""

from pytestqt.qtbot import QtBot

from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source
from snapcast_mvp.ui.widgets.group_card import GroupCard
from snapcast_mvp.ui.widgets.volume_slider import VolumeSlider


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
        assert not card._mute_button.isChecked()

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

        assert card._mute_button.isChecked()
        assert "Unmute" in card._mute_button.text()

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
