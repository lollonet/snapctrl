"""Group card widget - displays a group with volume control and source selection."""

from PySide6.QtCore import Signal
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
        self._name_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
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
        slider.volume_changed.connect(
            lambda vol: self.volume_changed.emit(self._group.id if self._group else "", vol)  # noqa: ARG005
        )
        self._volume_slider = slider
        return slider

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

    def _set_selected(self, selected: bool) -> None:
        """Set the visual selection state.

        Args:
            selected: Whether this card is selected.
        """
        self._selected = selected
        if selected:
            self.setStyleSheet(self._selected_style)
        else:
            self.setStyleSheet(self._base_style)

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

        self._source_combo.clear()
        for source in sources:
            self._source_combo.addItem(source.name, source.id)

        # Select current source for this group
        if self._group:
            index = self._source_combo.findData(self._group.stream_id)
            if index >= 0:
                self._source_combo.setCurrentIndex(index)

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

    def _update_client_cards(self, clients: list[Client]) -> None:
        """Update the client cards in the list.

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

            self._client_cards[client.id] = card
            self._clients_layout.addWidget(card)

        # Update the client count label
        self._client_list_label.setText(f"Clients: ({len(clients)})")

    def set_client_volume(self, client_id: str, volume: int) -> None:
        """Update volume for a specific client card.

        Args:
            client_id: The client ID.
            volume: New volume 0-100.
        """
        if client_id in self._client_cards:
            self._client_cards[client_id].set_volume(volume)

    def set_client_muted(self, client_id: str, muted: bool) -> None:
        """Update mute state for a specific client card.

        Args:
            client_id: The client ID.
            muted: New mute state.
        """
        if client_id in self._client_cards:
            self._client_cards[client_id].set_muted(muted)

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

        self._client_cards[client_id] = card
        self._clients_layout.addWidget(card)
