"""Groups panel - displays list of group cards in a scrollable area."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source
from snapcast_mvp.ui.theme import theme_manager
from snapcast_mvp.ui.widgets.group_card import GroupCard


class GroupsPanel(QWidget):
    """Center panel showing list of groups.

    Displays groups as interactive cards with volume controls,
    source selection, and expandable client lists.

    Example:
        panel = GroupsPanel()
        panel.set_groups(groups, sources)
        panel.volume_changed.connect(lambda gid, vol: handle_volume(gid, vol))
    """

    # Signals for group control
    volume_changed = Signal(str, int)  # group_id, volume
    mute_toggled = Signal(str, bool)  # group_id, muted
    source_changed = Signal(str, str)  # group_id, stream_id
    group_selected = Signal(str)  # group_id - emitted when a group card is clicked

    # Rename signals (forwarded from group/client cards)
    group_rename_requested = Signal(str, str)  # group_id, new_name
    client_rename_requested = Signal(str, str)  # client_id, new_name

    # Signals for client control (forwarded from group cards)
    client_volume_changed = Signal(str, int)  # client_id, volume
    client_mute_toggled = Signal(str, bool)  # client_id, muted
    client_selected = Signal(str)  # client_id - emitted when a client card is clicked

    def __init__(self) -> None:
        """Initialize the groups panel."""
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        p = theme_manager.palette
        header = QLabel("Groups")
        header.setStyleSheet(f"font-weight: bold; font-size: 12pt; color: {p.text};")
        layout.addWidget(header)

        # Scroll area for group cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)

        # Container widget for group cards
        self._container = QWidget()
        self._container.setStyleSheet("background-color: transparent;")
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(4, 4, 4, 4)
        self._container_layout.setSpacing(12)
        self._container_layout.addStretch()

        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        # Track group cards by ID
        self._group_cards: dict[str, GroupCard] = {}
        self._selected_group_id: str | None = None
        self._selected_client_id: str | None = None

    @property
    def selected_group_id(self) -> str | None:
        """Return the currently selected group ID."""
        return self._selected_group_id

    def set_selected_group(self, group_id: str) -> None:
        """Set the selected group.

        Args:
            group_id: The group ID to select.
        """
        self._selected_group_id = group_id

        # Update visual selection state on cards
        for gid, card in self._group_cards.items():
            card.set_selected(gid == group_id)

    def set_groups(
        self,
        groups: list[Group],
        sources: list[Source] | None = None,
        clients: dict[str, list[Client]] | None = None,
    ) -> None:
        """Update the list of groups.

        Args:
            groups: List of Group objects to display.
            sources: Optional list of available sources.
            clients: Optional dict mapping group_id to list of clients.
        """
        # Preserve expanded state before clearing
        expanded_groups: set[str] = {
            gid for gid, card in self._group_cards.items() if card.is_expanded
        }

        # Clear existing cards
        for card in self._group_cards.values():
            card.setParent(None)
        self._group_cards.clear()

        # Add new cards
        for group in groups:
            card = GroupCard(group)
            card.set_sources(sources or [])

            # Add client cards if available
            group_clients = clients.get(group.id) if clients else None
            if group_clients:
                card.update_clients(group_clients)

            # Connect card signals to panel signals
            card.volume_changed.connect(self.volume_changed.emit)
            card.mute_toggled.connect(self.mute_toggled.emit)
            card.source_changed.connect(self.source_changed.emit)
            card.clicked.connect(lambda gid=group.id: self._on_card_clicked(gid))

            # Connect client signals to panel signals
            card.client_volume_changed.connect(self.client_volume_changed.emit)
            card.client_mute_toggled.connect(self.client_mute_toggled.emit)
            card.client_clicked.connect(self.client_selected.emit)

            # Connect rename signals
            card.rename_requested.connect(self.group_rename_requested.emit)
            card.client_rename_requested.connect(self.client_rename_requested.emit)

            self._group_cards[group.id] = card
            # Insert before the stretch
            self._container_layout.insertWidget(self._container_layout.count() - 1, card)

            # Restore expanded state if it was expanded before
            if group.id in expanded_groups:
                card.set_expanded(True)

        # Restore selection if possible
        if self._selected_group_id and self._selected_group_id in self._group_cards:
            self.set_selected_group(self._selected_group_id)

    def _on_card_clicked(self, group_id: str) -> None:
        """Handle card click to select group.

        Args:
            group_id: The group ID that was clicked.
        """
        self.set_selected_group(group_id)
        self.group_selected.emit(group_id)

    def clear_groups(self) -> None:
        """Clear all groups from the panel."""
        for card in self._group_cards.values():
            card.setParent(None)
        self._group_cards.clear()

    def update_group(
        self,
        group: Group,
        sources: list[Source] | None = None,
        clients: list[Client] | None = None,
    ) -> None:
        """Update a specific group's card.

        Args:
            group: Group with updated data.
            sources: Optional list of available sources.
            clients: Optional list of clients for the group.
        """
        if group.id in self._group_cards:
            card = self._group_cards[group.id]
            card.update_from_state(group, sources or [], clients)

    def set_volume(self, group_id: str, volume: int) -> None:
        """Update volume for a specific group's card.

        Args:
            group_id: ID of the group.
            volume: New volume 0-100.
        """
        if group_id in self._group_cards:
            self._group_cards[group_id].set_volume(volume)

    def set_mute(self, group_id: str, muted: bool) -> None:
        """Update mute state for a specific group's card.

        Args:
            group_id: ID of the group.
            muted: New mute state.
        """
        if group_id in self._group_cards:
            # Use public API to update mute state without emitting signals
            self._group_cards[group_id].set_mute_state(muted)

    def set_client_volume(self, group_id: str, client_id: str, volume: int) -> None:
        """Update volume for a specific client card.

        Args:
            group_id: ID of the group.
            client_id: ID of the client.
            volume: New volume 0-100.
        """
        if group_id in self._group_cards:
            self._group_cards[group_id].set_client_volume(client_id, volume)

    def set_all_client_volumes(self, group_id: str, volumes: dict[str, int]) -> None:
        """Update volumes for all clients in a group (visual follow for group slider).

        Args:
            group_id: ID of the group.
            volumes: Dict mapping client_id -> volume (0-100).
        """
        if group_id in self._group_cards:
            self._group_cards[group_id].set_all_client_volumes(volumes)

    def set_client_muted(self, group_id: str, client_id: str, muted: bool) -> None:
        """Update mute state for a specific client card.

        Args:
            group_id: ID of the group.
            client_id: ID of the client.
            muted: New mute state.
        """
        if group_id in self._group_cards:
            self._group_cards[group_id].set_client_muted(client_id, muted)

    def set_selected_client(self, client_id: str | None) -> None:
        """Set the selected client across all groups.

        Args:
            client_id: The client ID to select, or None to deselect all.
        """
        self._selected_client_id = client_id
        # Clear client selection in all groups, then select in the right one
        for card in self._group_cards.values():
            card.set_selected_client(client_id)
