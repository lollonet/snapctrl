"""Client card widget - displays a client with volume control.

A compact widget for individual client control within a group card.
"""

from PySide6.QtCore import QEvent, QObject, Signal
from PySide6.QtGui import QContextMenuEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMenu,
)

from snapctrl.models.client import Client
from snapctrl.ui.theme import theme_manager
from snapctrl.ui.widgets.volume_slider import VolumeSlider


class ClientCard(QFrame):
    """Card widget for displaying and controlling a client.

    Uses QFrame for proper stylesheet support (background, border).

    Signals:
        volume_changed: Emitted when volume changes (client_id, volume).
        mute_toggled: Emitted when mute is toggled (client_id, muted).
        clicked: Emitted when card is clicked (client_id).

    Example:
        card = ClientCard(client_id="c1", name="Living Room", volume=50, muted=False)
        card.volume_changed.connect(lambda cid, vol: print(f"{cid}: {vol}"))
    """

    volume_changed = Signal(str, int)  # client_id, volume
    mute_toggled = Signal(str, bool)  # client_id, muted
    clicked = Signal(str)  # client_id
    rename_requested = Signal(str, str)  # client_id, new_name

    def __init__(
        self,
        client_id: str,
        name: str,
        volume: int = 50,
        muted: bool = False,
        connected: bool = True,
    ) -> None:
        """Initialize the client card.

        Args:
            client_id: The client ID.
            name: The client name.
            volume: Initial volume (0-100).
            muted: Initial mute state.
            connected: Whether the client is connected.
        """
        super().__init__()

        self._client_id = client_id
        self._name = name
        self._connected = connected

        self._setup_ui(volume, muted)

    def _setup_ui(self, volume: int, muted: bool) -> None:
        """Set up the user interface.

        Args:
            volume: Initial volume.
            muted: Initial mute state.
        """
        self._selected = False
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self._update_style(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Connection indicator (clickable)
        # Use filled circle with different colors: green=connected, red=disconnected
        p = theme_manager.palette
        self._status_indicator = QLabel("●")
        if self._connected:
            self._status_indicator.setStyleSheet(f"color: {p.success}; font-size: 14px;")
            self._status_indicator.setToolTip("Connected")
        else:
            self._status_indicator.setStyleSheet(f"color: {p.error}; font-size: 14px;")
            self._status_indicator.setToolTip("Disconnected")
        self._status_indicator.setCursor(self.cursor())
        self._status_indicator.installEventFilter(self)
        layout.addWidget(self._status_indicator)

        # Client name (clickable)
        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet(f"font-size: 10pt; color: {p.text}; padding: 4px;")
        self._name_label.setCursor(self.cursor())
        self._name_label.installEventFilter(self)
        layout.addWidget(self._name_label)

        layout.addStretch()

        # Volume slider (compact)
        self._volume_slider = VolumeSlider()
        self._volume_slider.set_volume(volume)
        self._volume_slider.set_muted(muted)
        self._volume_slider.volume_changed.connect(self._on_volume_changed)
        self._volume_slider.mute_toggled.connect(self._on_mute_toggled)
        layout.addWidget(self._volume_slider)

    def _on_volume_changed(self, volume: int) -> None:
        """Handle volume change from slider.

        Args:
            volume: New volume value.
        """
        self.volume_changed.emit(self._client_id, volume)

    def _on_mute_toggled(self, muted: bool) -> None:
        """Handle mute toggle from slider.

        Args:
            muted: New mute state.
        """
        self.mute_toggled.emit(self._client_id, muted)

    @property
    def client_id(self) -> str:
        """Return the client ID."""
        return self._client_id

    @property
    def name(self) -> str:
        """Return the client name."""
        return self._name

    def set_volume(self, volume: int) -> None:
        """Set the volume.

        Args:
            volume: Volume value 0-100.
        """
        self._volume_slider.set_volume(volume)

    def set_muted(self, muted: bool) -> None:
        """Set the mute state.

        Args:
            muted: Whether to mute.
        """
        self._volume_slider.set_muted(muted)

    def set_connected(self, connected: bool) -> None:
        """Update the connection status display.

        Args:
            connected: Whether the client is connected.
        """
        self._connected = connected
        # Always use filled circle, change color: green=connected, red=disconnected
        p = theme_manager.palette
        if connected:
            self._status_indicator.setStyleSheet(f"color: {p.success}; font-size: 14px;")
            self._status_indicator.setToolTip("Connected")
        else:
            self._status_indicator.setStyleSheet(f"color: {p.error}; font-size: 14px;")
            self._status_indicator.setToolTip("Disconnected")

    def set_selected(self, selected: bool) -> None:
        """Set the visual selection state.

        Args:
            selected: Whether this card is selected.
        """
        self._selected = selected
        self._update_style(selected)

    def _update_style(self, selected: bool) -> None:
        """Update the visual style based on selection state.

        Args:
            selected: Whether this card is selected.
        """
        p = theme_manager.palette
        if selected:
            self.setStyleSheet(f"""
                ClientCard {{
                    background-color: {p.surface_selected};
                    border-radius: 6px;
                    border: 2px solid {p.border_selected};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                ClientCard {{
                    background-color: {p.surface_dim};
                    border-radius: 6px;
                    border: 1px solid {p.border};
                }}
            """)

    def update_from_client(self, client: Client) -> None:
        """Update card from client data.

        Args:
            client: The client with updated data.
        """
        self._name = client.name
        self._name_label.setText(client.name)
        self.set_volume(client.volume)
        self.set_muted(client.muted)
        self.set_connected(client.connected)

    # noinspection PyMethodOverriding
    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        """Handle mouse press to emit clicked signal.

        Args:
            event: The mouse event.
        """
        # Don't call super() - this prevents event propagation to parent GroupCard
        event.accept()  # Mark as handled
        self.clicked.emit(self._client_id)

    # noinspection PyMethodOverriding
    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802
        """Show context menu on right-click.

        Args:
            event: The context menu event.
        """
        menu = QMenu(self)
        rename_action = menu.addAction("Rename...")
        action = menu.exec(event.globalPos())
        if action == rename_action:
            new_name, ok = QInputDialog.getText(
                self,
                "Rename Client",
                "New name:",
                text=self._name,
            )
            new_name = new_name.strip()
            if ok and new_name and new_name != self._name:
                self.rename_requested.emit(self._client_id, new_name)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # noqa: N802
        """Filter events from child widgets to handle clicks.

        Args:
            watched: The object being watched.
            event: The event.

        Returns:
            True if event was handled, False otherwise.
        """
        if event.type() == QEvent.Type.MouseButtonPress and watched in (
            self._name_label,
            self._status_indicator,
        ):
            self.clicked.emit(self._client_id)
            return True
        return super().eventFilter(watched, event)
