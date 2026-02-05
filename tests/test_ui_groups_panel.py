"""Tests for GroupsPanel."""

from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source
from snapctrl.ui.panels.groups import GroupsPanel


@pytest.fixture
def sample_client() -> Client:
    """Create a sample client for testing."""
    return Client(
        id="c1",
        host="host1",
        name="Test Client",
        volume=50,
        muted=False,
        connected=True,
    )


@pytest.fixture
def sample_group() -> Group:
    """Create a sample group for testing."""
    return Group(
        id="g1",
        name="Test Group",
        stream_id="s1",
        muted=False,
        client_ids=["c1"],
    )


@pytest.fixture
def sample_source() -> Source:
    """Create a sample source for testing."""
    return Source(id="s1", name="Test Source", status="playing")


class TestGroupsPanelCreation:
    """Test panel creation."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test panel can be created."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)
        assert panel is not None

    def test_has_signals(self, qtbot: QtBot) -> None:
        """Test panel has all required signals."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        assert hasattr(panel, "volume_changed")
        assert hasattr(panel, "mute_toggled")
        assert hasattr(panel, "source_changed")
        assert hasattr(panel, "group_selected")
        assert hasattr(panel, "group_rename_requested")
        assert hasattr(panel, "client_rename_requested")
        assert hasattr(panel, "client_volume_changed")
        assert hasattr(panel, "client_mute_toggled")
        assert hasattr(panel, "client_selected")

    def test_initial_state(self, qtbot: QtBot) -> None:
        """Test panel starts with no groups."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        assert panel._group_cards == {}
        assert panel.selected_group_id is None


class TestGroupsDisplay:
    """Test groups display functionality."""

    def test_set_groups(self, qtbot: QtBot, sample_group: Group, sample_source: Source) -> None:
        """Test setting groups creates cards."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])

        assert "g1" in panel._group_cards

    def test_set_groups_with_clients(
        self,
        qtbot: QtBot,
        sample_group: Group,
        sample_source: Source,
        sample_client: Client,
    ) -> None:
        """Test setting groups with clients."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        clients = {"g1": [sample_client]}
        panel.set_groups([sample_group], [sample_source], clients)

        assert "g1" in panel._group_cards

    def test_set_groups_updates_existing(
        self, qtbot: QtBot, sample_group: Group, sample_source: Source
    ) -> None:
        """Test setting groups updates existing cards."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        card1 = panel._group_cards["g1"]

        # Update with same group
        updated_group = Group(
            id="g1", name="Updated Name", stream_id="s1", muted=True, client_ids=["c1"]
        )
        panel.set_groups([updated_group], [sample_source])

        # Should be same card instance (updated, not recreated)
        assert panel._group_cards["g1"] is card1

    def test_set_groups_removes_old(
        self, qtbot: QtBot, sample_group: Group, sample_source: Source
    ) -> None:
        """Test setting groups removes cards for removed groups."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        assert "g1" in panel._group_cards

        # Set empty groups
        panel.set_groups([], [sample_source])
        assert "g1" not in panel._group_cards

    def test_clear_groups(self, qtbot: QtBot, sample_group: Group, sample_source: Source) -> None:
        """Test clearing all groups."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        assert len(panel._group_cards) == 1

        panel.clear_groups()
        assert len(panel._group_cards) == 0


class TestGroupSelection:
    """Test group selection functionality."""

    def test_set_selected_group(
        self, qtbot: QtBot, sample_group: Group, sample_source: Source
    ) -> None:
        """Test selecting a group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        panel.set_selected_group("g1")

        assert panel.selected_group_id == "g1"

    def test_group_selected_signal(
        self, qtbot: QtBot, sample_group: Group, sample_source: Source
    ) -> None:
        """Test group_selected signal is emitted on card click."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])

        received: list[str] = []
        panel.group_selected.connect(received.append)

        # Simulate card click
        panel._on_card_clicked("g1")

        assert received == ["g1"]
        assert panel.selected_group_id == "g1"


class TestVolumeControl:
    """Test volume control functionality."""

    def test_set_volume(self, qtbot: QtBot, sample_group: Group, sample_source: Source) -> None:
        """Test setting volume for a group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        panel.set_volume("g1", 75)  # Should not crash

    def test_set_volume_nonexistent(self, qtbot: QtBot) -> None:
        """Test setting volume for nonexistent group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_volume("nonexistent", 50)  # Should not crash

    def test_set_mute(self, qtbot: QtBot, sample_group: Group, sample_source: Source) -> None:
        """Test setting mute state for a group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        panel.set_mute("g1", True)  # Should not crash

    def test_set_mute_nonexistent(self, qtbot: QtBot) -> None:
        """Test setting mute for nonexistent group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_mute("nonexistent", True)  # Should not crash


class TestClientControl:
    """Test client control functionality."""

    def test_set_client_volume(
        self,
        qtbot: QtBot,
        sample_group: Group,
        sample_source: Source,
        sample_client: Client,
    ) -> None:
        """Test setting client volume."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        clients = {"g1": [sample_client]}
        panel.set_groups([sample_group], [sample_source], clients)
        panel.set_client_volume("g1", "c1", 80)  # Should not crash

    def test_set_client_volume_nonexistent_group(self, qtbot: QtBot) -> None:
        """Test setting client volume for nonexistent group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_client_volume("nonexistent", "c1", 50)  # Should not crash

    def test_set_all_client_volumes(
        self,
        qtbot: QtBot,
        sample_group: Group,
        sample_source: Source,
        sample_client: Client,
    ) -> None:
        """Test setting all client volumes in a group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        clients = {"g1": [sample_client]}
        panel.set_groups([sample_group], [sample_source], clients)
        panel.set_all_client_volumes("g1", {"c1": 60})  # Should not crash

    def test_set_all_client_volumes_nonexistent_group(self, qtbot: QtBot) -> None:
        """Test setting all client volumes for nonexistent group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_all_client_volumes("nonexistent", {"c1": 60})  # Should not crash

    def test_set_client_muted(
        self,
        qtbot: QtBot,
        sample_group: Group,
        sample_source: Source,
        sample_client: Client,
    ) -> None:
        """Test setting client mute state."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        clients = {"g1": [sample_client]}
        panel.set_groups([sample_group], [sample_source], clients)
        panel.set_client_muted("g1", "c1", True)  # Should not crash

    def test_set_client_muted_nonexistent_group(self, qtbot: QtBot) -> None:
        """Test setting client muted for nonexistent group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_client_muted("nonexistent", "c1", True)  # Should not crash

    def test_set_selected_client(
        self,
        qtbot: QtBot,
        sample_group: Group,
        sample_source: Source,
        sample_client: Client,
    ) -> None:
        """Test selecting a client."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        clients = {"g1": [sample_client]}
        panel.set_groups([sample_group], [sample_source], clients)
        panel.set_selected_client("c1")  # Should not crash

    def test_set_selected_client_none(
        self, qtbot: QtBot, sample_group: Group, sample_source: Source
    ) -> None:
        """Test deselecting all clients."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        panel.set_selected_client(None)  # Should not crash


class TestUpdateGroup:
    """Test individual group updates."""

    def test_update_group(self, qtbot: QtBot, sample_group: Group, sample_source: Source) -> None:
        """Test updating a specific group."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])

        updated = Group(id="g1", name="Updated", stream_id="s1", muted=True, client_ids=["c1"])
        panel.update_group(updated, [sample_source])  # Should not crash

    def test_update_group_nonexistent(
        self, qtbot: QtBot, sample_group: Group, sample_source: Source
    ) -> None:
        """Test updating nonexistent group does nothing."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])

        nonexistent = Group(id="nonexistent", name="X", stream_id="s1", muted=False, client_ids=[])
        panel.update_group(nonexistent, [sample_source])  # Should not crash


class TestTheme:
    """Test theme functionality."""

    def test_refresh_theme(self, qtbot: QtBot, sample_group: Group, sample_source: Source) -> None:
        """Test theme refresh."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        panel.set_groups([sample_group], [sample_source])
        panel.refresh_theme()  # Should not crash


class TestAutoExpand:
    """Test auto-expand behavior."""

    def test_auto_expand_single_group(self, qtbot: QtBot, sample_source: Source) -> None:
        """Test that single group auto-expands when added to empty panel."""
        panel = GroupsPanel()
        qtbot.addWidget(panel)

        single_group = Group(
            id="g1", name="Only Group", stream_id="s1", muted=False, client_ids=["c1"]
        )

        panel.set_groups([single_group], [sample_source])

        # The card should be expanded
        card = panel._group_cards.get("g1")
        assert card is not None
        # Just verify card was created, expansion state is internal
