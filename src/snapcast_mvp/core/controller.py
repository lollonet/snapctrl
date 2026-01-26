"""Controller - bridges UI signals to Snapcast API calls.

The Controller connects UI widget signals to the SnapcastClient API methods
and manages optimistic state updates through the StateStore.
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Slot

from snapcast_mvp.api.client import SnapcastClient
from snapcast_mvp.core.state import StateStore

if TYPE_CHECKING:
    from snapcast_mvp.ui.panels.groups import GroupsPanel

logger = logging.getLogger(__name__)


class Controller(QObject):
    """Controller connecting UI signals to API calls.

    The Controller acts as a bridge between UI widgets and the Snapcast
    server. It connects to widget signals and makes the appropriate API
    calls, while also updating the StateStore for optimistic UI updates.

    Example:
        controller = Controller(client, state_store)
        controller.connect_to_group_panel(groups_panel)

        # UI signal -> API call flow:
        # user clicks mute -> GroupCard.mute_toggled
        # -> Controller.on_group_mute_toggled
        # -> SnapcastClient.set_group_mute
        # -> StateStore.update_group_mute (optimistic)
    """

    def __init__(self, client: SnapcastClient, state_store: StateStore) -> None:
        """Initialize the controller.

        Args:
            client: The Snapcast API client.
            state_store: The state store for optimistic updates.
        """
        super().__init__()
        self._client = client
        self._state = state_store

    @Slot(str, int)
    async def on_group_volume_changed(self, group_id: str, volume: int) -> None:
        """Handle group volume change from UI.

        Args:
            group_id: The group ID.
            volume: New volume 0-100.
        """
        group = self._state.get_group(group_id)
        if not group:
            logger.warning(f"Volume change for unknown group: {group_id}")
            return

        # Set volume for all clients in the group
        clients = self._state.get_clients_for_group(group_id)
        for client in clients:
            if client:
                try:
                    await self._client.set_client_volume(
                        client.id,
                        volume,
                        client.muted,
                    )
                    # Optimistic update
                    self._state.update_client_volume(client.id, volume, client.muted)
                except Exception as e:
                    logger.error(f"Failed to set volume for {client.id}: {e}")

    @Slot(str, bool)
    async def on_group_mute_toggled(self, group_id: str, muted: bool) -> None:
        """Handle group mute toggle from UI.

        Args:
            group_id: The group ID.
            muted: New mute state.
        """
        group = self._state.get_group(group_id)
        if not group:
            logger.warning(f"Mute toggle for unknown group: {group_id}")
            return

        try:
            await self._client.set_group_mute(group_id, muted)
            # Optimistic update
            self._state.update_group_mute(group_id, muted)
        except Exception as e:
            logger.error(f"Failed to set mute for {group_id}: {e}")

    @Slot(str, str)
    async def on_group_source_changed(self, group_id: str, stream_id: str) -> None:
        """Handle group source change from UI.

        Args:
            group_id: The group ID.
            stream_id: The new stream ID.
        """
        group = self._state.get_group(group_id)
        if not group:
            logger.warning(f"Source change for unknown group: {group_id}")
            return

        try:
            await self._client.set_group_stream(group_id, stream_id)
        except Exception as e:
            logger.error(f"Failed to set stream for {group_id}: {e}")

    @Slot(str, int)
    async def on_client_volume_changed(self, client_id: str, volume: int) -> None:
        """Handle client volume change from UI.

        Args:
            client_id: The client ID.
            volume: New volume 0-100.
        """
        client = self._state.get_client(client_id)
        if not client:
            logger.warning(f"Volume change for unknown client: {client_id}")
            return

        try:
            await self._client.set_client_volume(
                client_id,
                volume,
                client.muted,
            )
            # Optimistic update
            self._state.update_client_volume(client_id, volume, client.muted)
        except Exception as e:
            logger.error(f"Failed to set volume for {client_id}: {e}")

    @Slot(str, bool)
    async def on_client_mute_toggled(self, client_id: str, muted: bool) -> None:
        """Handle client mute toggle from UI.

        Args:
            client_id: The client ID.
            muted: New mute state.
        """
        client = self._state.get_client(client_id)
        if not client:
            logger.warning(f"Mute toggle for unknown client: {client_id}")
            return

        try:
            await self._client.set_client_volume(
                client_id,
                client.volume,
                muted,
            )
            # Optimistic update
            self._state.update_client_volume(client_id, client.volume, muted)
        except Exception as e:
            logger.error(f"Failed to set mute for {client_id}: {e}")

    def connect_to_group_panel(self, panel: "GroupsPanel") -> None:
        """Connect controller slots to group panel signals.

        Args:
            panel: The GroupsPanel instance.
        """
        panel.volume_changed.connect(self.on_group_volume_changed)
        panel.mute_toggled.connect(self.on_group_mute_toggled)
        panel.source_changed.connect(self.on_group_source_changed)
        # Client control signals
        panel.client_volume_changed.connect(self.on_client_volume_changed)
        panel.client_mute_toggled.connect(self.on_client_mute_toggled)
