"""Group card widget - displays a group with volume control and source selection."""

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source
from snapcast_mvp.ui.widgets.client_card import ClientCard
from snapcast_mvp.ui.widgets.volume_slider import VolumeSlider


class GroupCard(QWidget):
    """Card widget for displaying and controlling a group.

    Shows group name, mute status, volume slider, source dropdown,
    and expandable client list with individual client controls.

    Example:
        card = GroupCard()
        card.set_group(Group(...))
        card.set_sources([Source(...)])
        card.volume_changed.connect(lambda gid, vol: print(f"{gid}: {vol}"))
    """

    # Signals for group control
    volume_changed = Signal(str, int)  # group_id, volume
    mute_toggled = Signal(str, bool)  # group_id, muted
    source_changed = Signal(str, str)  # group_id, stream_id
    expand_toggled = Signal(str, bool)  # group_id, expanded
    clicked = Signal()  # emitted when card is clicked

    # Signals for client control (forwarded from client cards)
    client_volume_changed = Signal(str, int)  # client_id, volume
    client_mute_toggled = Signal(str, bool)  # client_id, muted
    client_clicked = Signal(str)  # client_id

    def __init__(self, group: Group | None = None) -> None:
        """Initialize the group card.

        Args:
            group: Optional group to initialize with.
        """
        super().__init__()

        self._group = group
        self._sources: list[Source] = []
        self._expanded = False
        self._selected = False
        self._client_cards: dict[str, ClientCard] = {}

        self._setup_ui()

        if group:
            self._update_from_group()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self._setup_styles()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        layout.addLayout(self._create_header())
        layout.addWidget(self._create_mute_button())
        layout.addWidget(self._create_volume_slider())
        layout.addLayout(self._create_source_row())
        layout.addWidget(self._create_client_list())

    def _setup_styles(self) -> None:
        """Set up widget styles."""
        self._base_style = """
            GroupCard {
                background-color: #353535;
                border-radius: 8px;
                border: 1px solid #404040;
            }
        """
        self._selected_style = """
            GroupCard {
                background-color: #404050;
                border-radius: 8px;
                border: 2px solid #606080;
            }
        """
        self.setStyleSheet(self._base_style)

    def _create_header(self) -> QHBoxLayout:
        """Create the header row with name and expand button.

        Returns:
            The header layout.
        """
        header = QHBoxLayout()
        header.setSpacing(8)

        self._name_label = QLabel("Group Name")
        self._name_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 4px;")
        self._name_label.installEventFilter(self)
        header.addWidget(self._name_label)

        header.addStretch()

        self._expand_button = QPushButton("▼")
        self._expand_button.setFixedSize(24, 24)
        self._expand_button.setFlat(True)
        self._expand_button.setStyleSheet("QPushButton { border: none; }")
        self._expand_button.clicked.connect(self._toggle_expand)
        header.addWidget(self._expand_button)

        return header

    def _create_mute_button(self) -> QPushButton:
        """Create the mute toggle button.

        Returns:
            The mute button.
        """
        button = QPushButton("🔊 Mute")
        button.setCheckable(True)
        button.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
                border-radius: 4px;
                background-color: #404040;
            }
            QPushButton:checked {
                background-color: #604040;
            }
            QPushButton:hover {
                background-color: #505050;
            }
        """)
        button.clicked.connect(self._on_group_mute_toggled)
        self._mute_button = button
        return button

    def _create_volume_slider(self) -> VolumeSlider:
        """Create the volume slider.

        Returns:
            The volume slider widget.
        """
        slider = VolumeSlider()
        slider.volume_changed.connect(self._on_volume_slider_changed)
        self._volume_slider = slider
        return slider

    def _on_volume_slider_changed(self, vol: int) -> None:
        """Handle volume slider value changes."""
        group_id = self._group.id if self._group else ""
        self.volume_changed.emit(group_id, vol)

    def _create_source_row(self) -> QHBoxLayout:
        """Create the source selection row.

        Returns:
            The source row layout.
        """
        source_row = QHBoxLayout()
        source_row.setSpacing(8)

        source_label = QLabel("Source:")
        source_label.setStyleSheet("color: #808080;")
        source_row.addWidget(source_label)

        self._source_combo = QComboBox()
        self._source_combo.setMinimumWidth(120)
        self._source_combo.setStyleSheet("""
            QComboBox {
                padding: 4px;
                border-radius: 4px;
                background-color: #404040;
            }
        """)
        self._source_combo.currentTextChanged.connect(self._on_source_changed)
        source_row.addWidget(self._source_combo)

        source_row.addStretch()
        return source_row

    def _create_client_list(self) -> QWidget:
        """Create the expandable client list widget.

        Returns:
            The client list widget.
        """
        client_list = QWidget()
        client_list.setVisible(False)
        client_layout = QVBoxLayout(client_list)
        client_layout.setContentsMargins(8, 4, 8, 4)
        client_layout.setSpacing(4)

        self._client_list_label = QLabel("Clients:")
        self._client_list_label.setStyleSheet("color: #808080; font-size: 10pt;")
        client_layout.addWidget(self._client_list_label)

        self._clients_container = QWidget()
        self._clients_layout = QVBoxLayout(self._clients_container)
        self._clients_layout.setContentsMargins(0, 0, 0, 0)
        self._clients_layout.setSpacing(4)
        client_layout.addWidget(self._clients_container)

        self._client_list = client_list
        return client_list

    # noinspection PyMethodOverriding
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse press to emit clicked signal.

        Args:
            event: The mouse event.
        """
        super().mousePressEvent(event)
        self.clicked.emit()

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """Filter events from child widgets to handle clicks on name label.

        Args:
            watched: The object being watched.
            event: The event.

        Returns:
            True if event was handled, False otherwise.
        """
        if (
            event.type() == QEvent.Type.MouseButtonPress
            and watched is self._name_label
        ):
            self.clicked.emit()
            return True
        return super().eventFilter(watched, event)

    def _set_selected(self, selected: bool) -> None:
        """Internal: Set the visual selection state.

        Args:
            selected: Whether this card is selected.
        """
        self._selected = selected
        if selected:
            self.setStyleSheet(self._selected_style)
        else:
            self.setStyleSheet(self._base_style)

    def set_selected(self, selected: bool) -> None:
        """Set the visual selection state (public API).

        Args:
            selected: Whether this card is selected.
        """
        self._set_selected(selected)

    def set_group(self, group: Group) -> None:
        """Set the group for this card.

        Args:
            group: Group to display.
        """
        self._group = group
        self._update_from_group()

    def _update_from_group(self) -> None:
        """Update UI from group data."""
        if not self._group:
            return

        self._name_label.setText(self._group.name)

        # Update mute button
        self._mute_button.blockSignals(True)
        if self._group.muted:
            self._mute_button.setChecked(True)
            self._mute_button.setText("🔇 Unmute")
        else:
            self._mute_button.setChecked(False)
            self._mute_button.setText("🔊 Mute")
        self._mute_button.blockSignals(False)

        # Update volume slider
        self._volume_slider.set_muted(self._group.muted)

    def set_sources(self, sources: list[Source]) -> None:
        """Set available sources for the dropdown.

        Args:
            sources: List of available sources.
        """
        self._sources = sources

        # Block signals to avoid triggering source_changed during initialization
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        for source in sources:
            self._source_combo.addItem(source.name, source.id)

        # Select current source for this group
        if self._group:
            index = self._source_combo.findData(self._group.stream_id)
            if index >= 0:
                self._source_combo.setCurrentIndex(index)
        self._source_combo.blockSignals(False)

    def _on_group_mute_toggled(self, checked: bool) -> None:
        """Handle group mute toggle.

        Args:
            checked: Whether mute button is checked.
        """
        if checked:
            self._mute_button.setText("🔇 Unmute")
            self._volume_slider.set_muted(True)
        else:
            self._mute_button.setText("🔊 Mute")
            self._volume_slider.set_muted(False)

        self.mute_toggled.emit(self._group.id if self._group else "", checked)

    def _on_source_changed(self, _text: str) -> None:
        """Handle source dropdown change."""
        stream_id = self._source_combo.currentData()
        if stream_id:
            self.source_changed.emit(self._group.id if self._group else "", stream_id)

    def _toggle_expand(self) -> None:
        """Toggle expand/collapse of client list."""
        self._expanded = not self._expanded
        self._client_list.setVisible(self._expanded)
        self._expand_button.setText("▲" if self._expanded else "▼")
        self.expand_toggled.emit(self._group.id if self._group else "", self._expanded)

    @property
    def is_expanded(self) -> bool:
        """Return whether the client list is expanded."""
        return self._expanded

    def set_expanded(self, expanded: bool) -> None:
        """Set the expanded state without emitting signals.

        Args:
            expanded: Whether the client list should be expanded.
        """
        if self._expanded != expanded:
            self._expanded = expanded
            self._client_list.setVisible(expanded)
            self._expand_button.setText("▲" if expanded else "▼")

    def set_volume(self, volume: int) -> None:
        """Set the volume for this card.

        Args:
            volume: Volume 0-100.
        """
        self._volume_slider.set_volume(volume)

    def update_from_state(
        self,
        group: Group,
        sources: list[Source],
        clients: list[Client] | None = None,
    ) -> None:
        """Update card from current state.

        Args:
            group: Updated group data.
            sources: Available sources.
            clients: Optional list of clients for this group.
        """
        self._group = group
        self._update_from_group()

        # Update sources if changed
        if self._sources != sources:
            self.set_sources(sources)

        # Update client cards if provided
        if clients is not None:
            self._update_client_cards(clients)
            # Update group volume slider to reflect average of connected clients
            self._update_group_volume_from_clients(clients)

    def _update_client_cards(self, clients: list[Client]) -> None:
        """Internal: Update the client cards in the list.

        Args:
            clients: List of clients in this group.
        """
        # Clear existing client cards
        for card in self._client_cards.values():
            card.setParent(None)
        self._client_cards.clear()

        # Add new client cards
        for client in clients:
            card = ClientCard(
                client_id=client.id,
                name=client.name,
                volume=client.volume,
                muted=client.muted,
                connected=client.connected,
            )
            # Forward client signals
            card.volume_changed.connect(self.client_volume_changed.emit)
            card.mute_toggled.connect(self.client_mute_toggled.emit)
            card.clicked.connect(self.client_clicked.emit)

            self._client_cards[client.id] = card
            self._clients_layout.addWidget(card)

        # Update the client count label
        self._client_list_label.setText(f"Clients: ({len(clients)})")

    def _update_group_volume_from_clients(self, clients: list[Client]) -> None:
        """Update group volume slider to reflect average of connected clients.

        Args:
            clients: List of clients in this group.
        """
        # Calculate average volume of connected clients
        connected_clients = [c for c in clients if c.connected]
        if connected_clients:
            avg_volume = sum(c.volume for c in connected_clients) // len(connected_clients)
        elif clients:
            # Fall back to all clients if none connected
            avg_volume = sum(c.volume for c in clients) // len(clients)
        else:
            avg_volume = 50  # Default if no clients

        # Update slider without emitting signal
        self._volume_slider.set_volume(avg_volume)

    def update_clients(self, clients: list[Client]) -> None:
        """Update the client cards in the list (public API).

        Args:
            clients: List of clients in this group.
        """
        self._update_client_cards(clients)
        # Also update group volume slider to reflect client volumes
        self._update_group_volume_from_clients(clients)

    def set_client_volume(self, client_id: str, volume: int) -> None:
        """Update volume for a specific client card.

        Args:
            client_id: The client ID.
            volume: New volume 0-100.
        """
        if client_id in self._client_cards:
            self._client_cards[client_id].set_volume(volume)

    def set_all_client_volumes(self, volumes: dict[str, int]) -> None:
        """Update volumes for all client cards (visual follow for group slider).

        This updates the visual display without emitting signals.
        Use when the group slider moves to show clients following.

        Args:
            volumes: Dict mapping client_id -> volume (0-100).
        """
        for client_id, volume in volumes.items():
            if client_id in self._client_cards:
                self._client_cards[client_id].set_volume(volume)

    def set_selected_client(self, client_id: str | None) -> None:
        """Set which client is selected in this group.

        Args:
            client_id: The client ID to select, or None to deselect all.
        """
        for cid, card in self._client_cards.items():
            card.set_selected(cid == client_id)

    def set_client_muted(self, client_id: str, muted: bool) -> None:
        """Update mute state for a specific client card.

        Args:
            client_id: The client ID.
            muted: New mute state.
        """
        if client_id in self._client_cards:
            self._client_cards[client_id].set_muted(muted)

    def set_mute_state(self, muted: bool) -> None:
        """Set the mute state without emitting signals (for external updates).

        Use this when updating UI from server state to avoid signal cascades.

        Args:
            muted: Whether the group is muted.
        """
        self._mute_button.blockSignals(True)
        self._mute_button.setChecked(muted)
        if muted:
            self._mute_button.setText("🔇 Unmute")
        else:
            self._mute_button.setText("🔊 Mute")
        self._mute_button.blockSignals(False)

        self._volume_slider.set_muted(muted)

    def add_client(
        self,
        client_id: str,
        client_name: str,
        client_volume: int,
        client_muted: bool = False,
        client_connected: bool = True,
    ) -> None:
        """Add a client card to the client list.

        Args:
            client_id: The client ID.
            client_name: Name of the client.
            client_volume: Current volume.
            client_muted: Whether the client is muted.
            client_connected: Whether the client is connected.
        """
        card = ClientCard(
            client_id=client_id,
            name=client_name,
            volume=client_volume,
            muted=client_muted,
            connected=client_connected,
        )
        # Forward client signals
        card.volume_changed.connect(self.client_volume_changed.emit)
        card.mute_toggled.connect(self.client_mute_toggled.emit)
        card.clicked.connect(self.client_clicked.emit)

        self._client_cards[client_id] = card
        self._clients_layout.addWidget(card)
