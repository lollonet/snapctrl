"""Central state store with Qt signals for reactive UI updates.

The StateStore holds the current server state and emits Qt signals when
state changes. UI widgets connect to these signals to update themselves.

This follows the Observer pattern via Qt's signal/slot mechanism.
"""

import logging
from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.server import Server
from snapcast_mvp.models.server_state import ServerState
from snapcast_mvp.models.source import Source

logger = logging.getLogger(__name__)


class StateStore(QObject):
    """Central state store emitting Qt signals on changes.

    The StateStore maintains the current state of the Snapcast server
    and notifies subscribers via Qt signals when state changes occur.

    Signals are emitted from the worker thread via Qt's thread-safe
    signal delivery mechanism.

    Example:
        state = StateStore()

        # Connect a slot to be notified of group changes
        state.groups_changed.connect(lambda groups: print(f"Groups: {groups}"))

        # Update state (emits signals)
        state.update_from_server_state(server_state)
    """

    # Connection state signals
    connection_changed = Signal(bool)  # True=connected, False=disconnected

    # Data change signals - emit full lists on change
    # Note: Using object for complex types (PySide6 limitation)
    groups_changed = Signal(object)
    clients_changed = Signal(object)
    sources_changed = Signal(object)
    state_changed = Signal(object)  # Combined state signal

    def _is_connected(self) -> bool:
        """Internal check for connection state (before update)."""
        return self._state is not None and self._state.connected

    def __init__(self) -> None:
        """Initialize the state store with empty state."""
        super().__init__()
        self._state: ServerState | None = None
        self._groups: dict[str, Group] = {}
        self._clients: dict[str, Client] = {}
        self._sources: dict[str, Source] = {}

    @property
    def is_connected(self) -> bool:
        """Return True if currently connected to a server."""
        return self._is_connected()

    @property
    def server(self) -> Server | None:
        """Return the current server info, or None if disconnected."""
        return self._state.server if self._state else None

    @property
    def groups(self) -> list[Group]:
        """Return all groups."""
        return list(self._groups.values())

    @property
    def clients(self) -> list[Client]:
        """Return all clients."""
        return list(self._clients.values())

    @property
    def sources(self) -> list[Source]:
        """Return all sources."""
        return list(self._sources.values())

    def get_group(self, group_id: str) -> Group | None:
        """Get a group by ID.

        Args:
            group_id: The group ID to look up.

        Returns:
            The Group if found, else None.
        """
        return self._groups.get(group_id)

    def get_client(self, client_id: str) -> Client | None:
        """Get a client by ID.

        Args:
            client_id: The client ID to look up.

        Returns:
            The Client if found, else None.
        """
        return self._clients.get(client_id)

    def get_source(self, source_id: str) -> Source | None:
        """Get a source by ID.

        Args:
            source_id: The source ID to look up.

        Returns:
            The Source if found, else None.
        """
        return self._sources.get(source_id)

    def get_clients_for_group(self, group_id: str) -> list[Client]:
        """Get all clients belonging to a group.

        Args:
            group_id: The group ID.

        Returns:
            List of clients in the group, or empty list if group not found.
        """
        group = self._groups.get(group_id)
        if not group:
            return []
        result: list[Client] = []
        for cid in group.client_ids:
            client = self._clients.get(cid)
            if client:
                result.append(client)
        return result

    def get_group_for_client(self, client_id: str) -> Group | None:
        """Find the group that contains a client.

        Args:
            client_id: The client ID.

        Returns:
            The Group containing the client, or None if not found.
        """
        for group in self._groups.values():
            if client_id in group.client_ids:
                return group
        return None

    def update_from_server_state(self, state: ServerState) -> None:
        """Update internal state from ServerState and emit signals.

        Compares the new state with the current state and emits signals
        only for data that actually changed.

        Args:
            state: The new server state.
        """
        # Check connection state BEFORE updating
        was_connected = self._is_connected()
        connection_changed = state.connected != was_connected

        # Now update the state
        self._state = state

        # Convert lists to dicts for easier lookup/comparison
        new_groups = {g.id: g for g in state.groups}
        new_clients = {c.id: c for c in state.clients}
        new_sources = {s.id: s for s in state.sources}

        # Store all values FIRST, then emit signals
        # (handlers may read other properties, so all must be updated)
        groups_changed = new_groups != self._groups
        clients_changed = new_clients != self._clients
        sources_changed = new_sources != self._sources

        self._groups = new_groups
        self._clients = new_clients

        # Merge sources: preserve metadata we've added (from MpdMonitor etc.)
        # when Snapcast server sends updates with empty metadata
        merged_sources: dict[str, Source] = {}
        for source_id, new_source in new_sources.items():
            old_source = self._sources.get(source_id)
            if old_source and old_source.has_metadata and not new_source.has_metadata:
                # Preserve our metadata if server sends empty metadata
                merged_sources[source_id] = replace(
                    new_source,
                    meta_title=old_source.meta_title,
                    meta_artist=old_source.meta_artist,
                    meta_album=old_source.meta_album,
                    meta_art_url=old_source.meta_art_url,
                )
            else:
                merged_sources[source_id] = new_source
        self._sources = merged_sources

        # Now emit signals (handlers can safely read any property)
        if groups_changed:
            self.groups_changed.emit(state.groups)

        if clients_changed:
            self.clients_changed.emit(state.clients)

        if sources_changed:
            self.sources_changed.emit(list(merged_sources.values()))

        # Emit connection state if changed (including initial connection)
        if connection_changed:
            self.connection_changed.emit(state.connected)

        # Always emit state_changed for full updates
        self.state_changed.emit(state)

    def update_client_volume(self, client_id: str, volume: int, muted: bool) -> None:
        """Update a specific client's volume in the local state.

        This is used for optimistic UI updates before the server confirms.

        Args:
            client_id: The client ID.
            volume: New volume 0-100.
            muted: New mute state.
        """
        client = self._clients.get(client_id)
        if client:
            updated = replace(client, volume=volume, muted=muted)
            self._clients[client_id] = updated

            # Rebuild clients list and emit
            new_clients = list(self._clients.values())
            self.clients_changed.emit(new_clients)

            # Update state if we have it
            if self._state:
                # Update clients in state
                new_state_clients = [
                    updated if c.id == client_id else c for c in self._state.clients
                ]
                self._state = replace(self._state, clients=new_state_clients)
                self.state_changed.emit(self._state)

    def update_group_mute(self, group_id: str, muted: bool) -> None:
        """Update a specific group's mute state in the local state.

        Args:
            group_id: The group ID.
            muted: New mute state.
        """
        group = self._groups.get(group_id)
        if group:
            updated = replace(group, muted=muted)
            self._groups[group_id] = updated

            # Rebuild groups list and emit
            new_groups = list(self._groups.values())
            self.groups_changed.emit(new_groups)

            # Update state if we have it
            if self._state:
                new_state_groups = [updated if g.id == group_id else g for g in self._state.groups]
                self._state = replace(self._state, groups=new_state_groups)
                self.state_changed.emit(self._state)

    def update_source_metadata(
        self,
        source_id: str,
        *,
        meta_title: str = "",
        meta_artist: str = "",
        meta_album: str = "",
        meta_art_url: str = "",
    ) -> None:
        """Update a source's track metadata.

        This is used to inject metadata from external sources (e.g., MPD).

        Args:
            source_id: The source ID to update.
            meta_title: Track title.
            meta_artist: Track artist.
            meta_album: Track album.
            meta_art_url: Album art URL (data URI or http).
        """
        source = self._sources.get(source_id)
        if not source:
            logger.debug(
                "Cannot update metadata: source '%s' not found (available: %s)",
                source_id,
                list(self._sources.keys()),
            )
            return

        # Update source with new metadata
        updated = replace(
            source,
            meta_title=meta_title,
            meta_artist=meta_artist,
            meta_album=meta_album,
            meta_art_url=meta_art_url,
        )
        self._sources[source_id] = updated

        # Emit sources changed
        self.sources_changed.emit(list(self._sources.values()))

        # Update state if we have it
        if self._state:
            new_state_sources = tuple(
                updated if s.id == source_id else s for s in self._state.sources
            )
            self._state = replace(self._state, sources=new_state_sources)
            self.state_changed.emit(self._state)

    def find_source_by_name(self, name: str) -> Source | None:
        """Find a source by name (case-insensitive).

        Args:
            name: Source name to search for.

        Returns:
            The Source if found, else None.
        """
        return self._find_source_by_attribute("name", name)

    def find_source_by_scheme(self, scheme: str) -> Source | None:
        """Find a source by URI scheme.

        Args:
            scheme: URI scheme (e.g., "pipe", "librespot", "airplay").

        Returns:
            The first matching Source, or None.
        """
        return self._find_source_by_attribute("uri_scheme", scheme)

    def _find_source_by_attribute(self, attribute: str, value: str) -> Source | None:
        """Find a source by matching an attribute value (case-insensitive).

        Args:
            attribute: The attribute name to check.
            value: The value to match.

        Returns:
            The Source if found, else None.
        """
        value_lower = value.lower()
        for source in self._sources.values():
            source_value = getattr(source, attribute, "")
            if source_value.lower() == value_lower:
                return source
        return None

    def clear(self) -> None:
        """Clear all state (disconnected)."""
        was_connected = self.is_connected
        self._state = None
        self._groups.clear()
        self._clients.clear()
        self._sources.clear()

        if was_connected:
            self.connection_changed.emit(False)
