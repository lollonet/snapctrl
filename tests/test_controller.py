"""Tests for the Controller."""

from unittest.mock import AsyncMock, Mock

import pytest

from snapctrl.api.client import SnapcastClient
from snapctrl.core.controller import Controller
from snapctrl.core.state import StateStore
from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source


@pytest.fixture
def mock_client() -> Mock:
    """Create a mock API client."""
    client = Mock(spec=SnapcastClient)
    client.set_client_volume = AsyncMock()
    client.set_group_mute = AsyncMock()
    client.set_group_stream = AsyncMock()
    return client


@pytest.fixture
def state_store() -> StateStore:
    """Create a StateStore with test data."""
    store = StateStore()

    # Add test data
    groups = [
        Group(id="g1", name="Living Room", stream_id="s1", muted=False, client_ids=["c1", "c2"]),
        Group(id="g2", name="Bedroom", stream_id="s1", muted=True, client_ids=["c3"]),
    ]

    clients = [
        Client(
            id="c1", host="192.168.1.10", name="Player One", volume=50, muted=False, connected=True
        ),
        Client(
            id="c2", host="192.168.1.11", name="Player Two", volume=75, muted=False, connected=True
        ),
        Client(
            id="c3",
            host="192.168.1.12",
            name="Bedroom Player",
            volume=60,
            muted=True,
            connected=True,
        ),
    ]

    sources = [
        Source(id="s1", name="MPD", status="playing", stream_type="flac"),
        Source(id="s2", name="Spotify", status="idle", stream_type="ogg"),
    ]

    # Manually populate the store
    store._groups = {g.id: g for g in groups}
    store._clients = {c.id: c for c in clients}
    store._sources = {s.id: s for s in sources}

    return store


@pytest.fixture
def controller(mock_client: Mock, state_store: StateStore) -> Controller:
    """Create a Controller with mock dependencies."""
    return Controller(mock_client, state_store)


class TestControllerCreation:
    """Test Controller initialization."""

    def test_creation(self, mock_client: Mock, state_store: StateStore) -> None:
        """Test that controller can be created."""
        controller = Controller(mock_client, state_store)
        assert controller._client is mock_client
        assert controller._state is state_store


class TestGroupVolumeControl:
    """Test group volume control methods."""

    @pytest.mark.asyncio
    async def test_on_group_volume_changed(
        self, controller: Controller, mock_client: Mock, state_store: StateStore
    ) -> None:
        """Test handling group volume change."""
        await controller.on_group_volume_changed("g1", 80)

        # Should call set_client_volume for each client in group
        assert mock_client.set_client_volume.call_count == 2

        # Check first call (client c1)
        call_args = mock_client.set_client_volume.call_args_list[0]
        assert call_args[0][0] == "c1"
        assert call_args[0][1] == 80

    @pytest.mark.asyncio
    async def test_on_group_volume_unknown_group(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test handling volume change for unknown group."""
        await controller.on_group_volume_changed("unknown", 50)

        # Should not call API
        assert mock_client.set_client_volume.call_count == 0


class TestGroupMuteControl:
    """Test group mute control methods."""

    @pytest.mark.asyncio
    async def test_on_group_mute_toggled(self, controller: Controller, mock_client: Mock) -> None:
        """Test handling group mute toggle."""
        await controller.on_group_mute_toggled("g1", True)

        # Should call set_group_mute
        mock_client.set_group_mute.assert_called_once_with("g1", True)

    @pytest.mark.asyncio
    async def test_on_group_mute_unknown_group(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test handling mute toggle for unknown group."""
        await controller.on_group_mute_toggled("unknown", True)

        # Should not call API
        assert mock_client.set_group_mute.call_count == 0


class TestGroupSourceControl:
    """Test group source selection methods."""

    @pytest.mark.asyncio
    async def test_on_group_source_changed(self, controller: Controller, mock_client: Mock) -> None:
        """Test handling group source change."""
        await controller.on_group_source_changed("g1", "s2")

        # Should call set_group_stream
        mock_client.set_group_stream.assert_called_once_with("g1", "s2")


class TestClientVolumeControl:
    """Test client volume control methods."""

    @pytest.mark.asyncio
    async def test_on_client_volume_changed(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test handling client volume change."""
        await controller.on_client_volume_changed("c1", 90)

        # Should call set_client_volume
        mock_client.set_client_volume.assert_called_once_with("c1", 90, False)

    @pytest.mark.asyncio
    async def test_on_client_volume_unknown_client(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test handling volume change for unknown client."""
        await controller.on_client_volume_changed("unknown", 50)

        # Should not call API
        assert mock_client.set_client_volume.call_count == 0


class TestClientMuteControl:
    """Test client mute control methods."""

    @pytest.mark.asyncio
    async def test_on_client_mute_toggled(self, controller: Controller, mock_client: Mock) -> None:
        """Test handling client mute toggle."""
        await controller.on_client_mute_toggled("c1", True)

        # Should call set_client_volume with mute flag
        mock_client.set_client_volume.assert_called_once_with("c1", 50, True)


class TestSignalConnection:
    """Test signal connection to panels."""

    def test_controller_has_slot_methods(self, controller: Controller) -> None:
        """Test that controller has all required slot methods."""
        # Verify controller has the slot methods
        assert hasattr(controller, "on_group_volume_changed")
        assert hasattr(controller, "on_group_mute_toggled")
        assert hasattr(controller, "on_group_source_changed")
        assert hasattr(controller, "on_client_volume_changed")
        assert hasattr(controller, "on_client_mute_toggled")
        assert hasattr(controller, "connect_to_group_panel")


class TestControllerExceptionHandling:
    """Test exception handling in controller methods."""

    @pytest.mark.asyncio
    async def test_group_volume_error_handling(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test error handling during group volume change."""
        mock_client.set_client_volume.side_effect = Exception("API error")

        # Should not raise, just log
        await controller.on_group_volume_changed("g1", 50)

    @pytest.mark.asyncio
    async def test_group_mute_error_handling(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test error handling during group mute toggle."""
        mock_client.set_group_mute.side_effect = Exception("API error")

        # Should not raise, just log
        await controller.on_group_mute_toggled("g1", True)

    @pytest.mark.asyncio
    async def test_group_source_error_handling(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test error handling during group source change."""
        mock_client.set_group_stream.side_effect = Exception("API error")

        # Should not raise, just log
        await controller.on_group_source_changed("g1", "s2")

    @pytest.mark.asyncio
    async def test_client_volume_error_handling(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test error handling during client volume change."""
        mock_client.set_client_volume.side_effect = Exception("API error")

        # Should not raise, just log
        await controller.on_client_volume_changed("c1", 50)

    @pytest.mark.asyncio
    async def test_client_mute_error_handling(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test error handling during client mute toggle."""
        mock_client.set_client_volume.side_effect = Exception("API error")

        # Should not raise, just log
        await controller.on_client_mute_toggled("c1", True)


class TestConnectToGroupPanel:
    """Test connect_to_group_panel method."""

    def test_connect_to_group_panel(self, controller: Controller) -> None:
        """Test connecting to a mock group panel."""
        mock_panel = Mock()
        mock_panel.volume_changed = Mock()
        mock_panel.mute_toggled = Mock()
        mock_panel.source_changed = Mock()
        mock_panel.client_volume_changed = Mock()
        mock_panel.client_mute_toggled = Mock()

        controller.connect_to_group_panel(mock_panel)

        # Verify all signals were connected
        mock_panel.volume_changed.connect.assert_called_once()
        mock_panel.mute_toggled.connect.assert_called_once()
        mock_panel.source_changed.connect.assert_called_once()
        mock_panel.client_volume_changed.connect.assert_called_once()
        mock_panel.client_mute_toggled.connect.assert_called_once()


class TestUnknownClientMute:
    """Test client mute with unknown client."""

    @pytest.mark.asyncio
    async def test_on_client_mute_unknown_client(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test handling mute toggle for unknown client."""
        await controller.on_client_mute_toggled("unknown", True)

        # Should not call API
        assert mock_client.set_client_volume.call_count == 0


class TestGroupSourceUnknownGroup:
    """Test group source with unknown group."""

    @pytest.mark.asyncio
    async def test_on_group_source_unknown_group(
        self, controller: Controller, mock_client: Mock
    ) -> None:
        """Test handling source change for unknown group."""
        await controller.on_group_source_changed("unknown", "s1")

        # Should not call API
        assert mock_client.set_group_stream.call_count == 0
