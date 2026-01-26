"""Tests for UI panels."""

from pytestqt.qtbot import QtBot

from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source
from snapcast_mvp.ui.panels.groups import GroupsPanel
from snapcast_mvp.ui.panels.properties import PropertiesPanel
from snapcast_mvp.ui.panels.sources import SourcesPanel


class TestSourcesPanel:
    """Test SourcesPanel."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that sources panel can be created."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)
        assert panel._list is not None

    def test_set_sources(self, qtbot: QtBot) -> None:
        """Test setting sources."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        sources = [
            Source(id="1", name="MPD", status="playing", stream_type="flac"),
            Source(id="2", name="Spotify", status="idle", stream_type="ogg"),
        ]
        panel.set_sources(sources)

        assert panel._list.count() == 2

    def test_playing_indicator(self, qtbot: QtBot) -> None:
        """Test that playing sources show indicator."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        sources = [
            Source(id="1", name="Playing", status="playing", stream_type="flac"),
            Source(id="2", name="Idle", status="idle", stream_type="ogg"),
        ]
        panel.set_sources(sources)

        # First item should have playing indicator
        first_item = panel._list.item(0)
        assert "▶" in first_item.text()

    def test_clear_sources(self, qtbot: QtBot) -> None:
        """Test clearing sources."""
        panel = SourcesPanel()
        qtbot.addWidget(panel)

        sources = [Source(id="1", name="Test", status="idle", stream_type="flac")]
        panel.set_sources(sources)
        assert panel._list.count() == 1

        panel.clear_sources()
        assert panel._list.count() == 0


class TestGroupsPanel:
    """Test GroupsPanel."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that groups panel can be created."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)
        assert panel._container is not None

    def test_set_groups(self, qtbot: QtBot) -> None:
        """Test setting groups."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        groups = [
            Group(id="g1", name="Living Room", stream_id="mpd", muted=False, client_ids=["c1"]),
            Group(id="g2", name="Bedroom", stream_id="mpd", muted=True, client_ids=["c2"]),
        ]
        panel.set_groups(groups)

        assert len(panel._group_cards) == 2

    def test_clear_groups(self, qtbot: QtBot) -> None:
        """Test clearing groups."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        groups = [Group(id="g1", name="Test", stream_id="s", muted=False, client_ids=[])]
        panel.set_groups(groups)
        assert len(panel._group_cards) == 1

        panel.clear_groups()
        assert len(panel._group_cards) == 0

    def test_update_group(self, qtbot: QtBot) -> None:
        """Test updating a specific group card."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        groups = [Group(id="g1", name="Test", stream_id="s", muted=False, client_ids=[])]
        panel.set_groups(groups)
        assert len(panel._group_cards) == 1

        # Update with muted group
        updated = Group(id="g1", name="Test", stream_id="s", muted=True, client_ids=[])
        panel.update_group(updated)
        assert len(panel._group_cards) == 1


class TestPropertiesPanel:
    """Test PropertiesPanel."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that properties panel can be created."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert panel._content is not None

    def test_initially_shows_placeholder(self, qtbot: QtBot) -> None:
        """Test that panel shows placeholder initially."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        text = panel._content.text()
        assert "Select an item" in text

    def test_set_group(self, qtbot: QtBot) -> None:
        """Test setting group properties."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        group = Group(id="g1", name="Living Room", stream_id="mpd", muted=False, client_ids=["c1"])
        panel.set_group(group)

        text = panel._content.text()
        assert "Living Room" in text

    def test_set_client(self, qtbot: QtBot) -> None:
        """Test setting client properties."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        client = Client(
            id="c1", host="192.168.1.100", name="Player", volume=50, muted=False, connected=True
        )
        panel.set_client(client)

        text = panel._content.text()
        assert "Player" in text or "192.168.1.100" in text

    def test_set_source(self, qtbot: QtBot) -> None:
        """Test setting source properties."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        source = Source(id="s1", name="MPD", status="playing", stream_type="flac")
        panel.set_source(source)

        text = panel._content.text()
        assert "MPD" in text

    def test_clear(self, qtbot: QtBot) -> None:
        """Test clearing properties."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        group = Group(id="g1", name="Test", stream_id="s", muted=False, client_ids=[])
        panel.set_group(group)
        assert "Test" in panel._content.text()

        panel.clear()
        assert "Select an item" in panel._content.text()
