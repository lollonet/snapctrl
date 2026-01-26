"""Client card widget - displays a client with volume control.

A compact widget for individual client control within a group card.
"""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QWidget,
)

from snapcast_mvp.models.client import Client
from snapcast_mvp.ui.widgets.volume_slider import VolumeSlider


class ClientCard(QWidget):
    """Card widget for displaying and controlling a client.

    Shows client name, connection status, volume slider, and mute button.

    Signals:
        volume_changed: Emitted when volume changes (client_id, volume).
        mute_toggled: Emitted when mute is toggled (client_id, muted).

    Example:
        card = ClientCard(client_id="c1", name="Living Room", volume=50, muted=False)
        card.volume_changed.connect(lambda cid, vol: print(f"{cid}: {vol}"))
    """

    volume_changed = Signal(str, int)  # client_id, volume
    mute_toggled = Signal(str, bool)  # client_id, muted

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
        self.setStyleSheet("""
            ClientCard {
                background-color: #2a2a2a;
                border-radius: 6px;
                border: 1px solid #333333;
                padding: 4px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        # Connection indicator
        self._status_indicator = QLabel("●" if self._connected else "○")
        self._status_indicator.setStyleSheet(
            "color: #4CAF50;" if self._connected else "color: #757575;"
        )
        self._status_indicator.setToolTip("Connected" if self._connected else "Disconnected")
        layout.addWidget(self._status_indicator)

        # Client name
        self._name_label = QLabel(self._name)
        self._name_label.setStyleSheet("font-size: 10pt; color: #e0e0e0;")
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
        self._status_indicator.setText("●" if connected else "○")
        self._status_indicator.setStyleSheet(
            "color: #4CAF50;" if connected else "color: #757575;"
        )
        self._status_indicator.setToolTip("Connected" if connected else "Disconnected")

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
