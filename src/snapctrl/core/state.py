"""Central state store with Qt signals for reactive UI updates.

The StateStore holds the current server state and emits Qt signals when
state changes. UI widgets connect to these signals to update themselves.

This follows the Observer pattern via Qt's signal/slot mechanism.
"""

import logging
from collections.abc import Mapping
from dataclasses import replace

from PySide6.QtCore import QObject, Signal

from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.server import Server
from snapctrl.models.server_state import ServerState
from snapctrl.models.source import Source

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
        # List caches to avoid repeated list() conversions
        self._groups_cache: list[Group] | None = None
        self._clients_cache: list[Client] | None = None
        self._sources_cache: list[Source] | None = None

    @property
    def is_connected(self) -> bool:
        """Return True if currently connected to a server."""
        return self._is_connected()

    @property
    def server(self) -> Server | None:
        """Return the current server info, or None if disconnected."""
        return self._state.server if self._state else None

    @property
    def server_version(self) -> str:
        """Return the snapserver version string, or empty if unknown."""
        return self._state.version if self._state else ""

    @property
    def groups(self) -> list[Group]:
        """Return all groups (cached)."""
        if self._groups_cache is None:
            self._groups_cache = list(self._groups.values())
        return self._groups_cache

    @property
    def clients(self) -> list[Client]:
        """Return all clients (cached)."""
        if self._clients_cache is None:
            self._clients_cache = list(self._clients.values())
        return self._clients_cache

    @property
    def sources(self) -> list[Source]:
        """Return all sources (cached)."""
        if self._sources_cache is None:
            self._sources_cache = list(self._sources.values())
        return self._sources_cache

    def _invalidate_caches(self) -> None:
        """Invalidate all list caches."""
        self._groups_cache = None
        self._clients_cache = None
        self._sources_cache = None

    @staticmethod
    def _dict_changed(old: Mapping[str, object], new: Mapping[str, object]) -> bool:
        """Check if dictionary changed using optimized comparison.

        First compares keys (fast set operation), then compares values
        only for matching keys. This avoids expensive deep comparison
        when keys differ.
        """
        # Fast path: different key sets
        if old.keys() != new.keys():
            return True
        # Slow path: compare values only if keys match
        return any(old[k] != new[k] for k in new)

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

        # Optimized change detection: check keys first (fast), then values only if needed
        groups_changed = self._dict_changed(self._groups, new_groups)
        clients_changed = self._dict_changed(self._clients, new_clients)
        sources_changed = self._dict_changed(self._sources, new_sources)

        # Update dictionaries and invalidate caches
        if groups_changed:
            self._groups = new_groups
            self._groups_cache = None
        if clients_changed:
            self._clients = new_clients
            self._clients_cache = None

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
            elif (
                old_source
                and old_source.meta_art_url
                and old_source.meta_art_url.startswith("data:")
            ):
                # Prefer locally-fetched art (data URI) over server HTTP URLs
                # Data URIs are from MPD embedded art which is more reliable
                merged_sources[source_id] = replace(
                    new_source,
                    meta_art_url=old_source.meta_art_url,
                )
            else:
                merged_sources[source_id] = new_source

        # Check if sources changed (either from dict comparison above, or from merging)
        # Set sources_changed here so signal emission below is triggered
        if sources_changed or merged_sources != self._sources:
            self._sources = merged_sources
            self._sources_cache = None
            sources_changed = True  # Ensure signal is emitted below

        # Now emit signals (handlers can safely read any property)
        if groups_changed:
            self.groups_changed.emit(state.groups)

        if clients_changed:
            self.clients_changed.emit(state.clients)

        if sources_changed:
            self.sources_changed.emit(self.sources)  # Use cached property

        # Emit connection state if changed (including initial connection)
        if connection_changed:
            self.connection_changed.emit(state.connected)

        # Only emit state_changed if no specific signals were emitted
        # This prevents double UI updates when specific handlers already processed
        if not (groups_changed or clients_changed or sources_changed or connection_changed):
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
            self._clients_cache = None  # Invalidate cache

            # Emit using cached property
            self.clients_changed.emit(self.clients)

            # Update state if we have it (but don't emit state_changed)
            if self._state:
                new_state_clients = [
                    updated if c.id == client_id else c for c in self._state.clients
                ]
                self._state = replace(self._state, clients=new_state_clients)

    def update_client_latency(self, client_id: str, latency: int) -> None:
        """Update a specific client's latency offset in the local state.

        Args:
            client_id: The client ID.
            latency: New latency offset in milliseconds.
        """
        client = self._clients.get(client_id)
        if client:
            updated = replace(client, latency=latency)
            self._clients[client_id] = updated
            self._clients_cache = None  # Invalidate cache

            self.clients_changed.emit(self.clients)

            # Update state but don't emit state_changed (clients_changed is sufficient)
            if self._state:
                new_state_clients = [
                    updated if c.id == client_id else c for c in self._state.clients
                ]
                self._state = replace(self._state, clients=new_state_clients)

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
            self._groups_cache = None  # Invalidate cache

            # Emit using cached property
            self.groups_changed.emit(self.groups)

            # Update state but don't emit state_changed (groups_changed is sufficient)
            if self._state:
                new_state_groups = [updated if g.id == group_id else g for g in self._state.groups]
                self._state = replace(self._state, groups=new_state_groups)

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
        self._sources_cache = None  # Invalidate cache

        # Emit sources changed (no state_changed to avoid double updates)
        self.sources_changed.emit(self.sources)

        # Update state but don't emit state_changed (sources_changed is sufficient)
        if self._state:
            new_state_sources = tuple(
                updated if s.id == source_id else s for s in self._state.sources
            )
            self._state = replace(self._state, sources=new_state_sources)

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
        self._invalidate_caches()

        if was_connected:
            self.connection_changed.emit(False)
