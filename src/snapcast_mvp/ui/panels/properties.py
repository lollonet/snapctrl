"""Properties panel - displays details of selected item."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QVBoxLayout,
    QWidget,
)

from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source


class PropertiesPanel(QWidget):
    """Right panel showing details of selected item.

    Displays properties of the currently selected group, client, or source.
    Shows nothing when nothing is selected.

    Example:
        panel = PropertiesPanel()
        panel.set_group(selected_group)
        panel.clear()
    """

    def __init__(self) -> None:
        """Initialize the properties panel."""
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QLabel("Properties")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)

        # Content area (placeholder for now)
        self._content = QLabel("Select an item to see details")
        self._content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.setStyleSheet("color: #606060; font-style: italic;")
        layout.addWidget(self._content)

        layout.addStretch()

    def clear(self) -> None:
        """Clear the properties panel."""
        self._content.setText("Select an item to see details")
        self._content.setStyleSheet("color: #606060; font-style: italic;")

    def set_group(self, group: Group) -> None:
        """Display group properties.

        Args:
            group: Group to display.
        """
        mute_status = "Muted" if group.muted else "Active"
        html = f"""
            <h3>{group.name}</h3>
            <table cellpadding="4">
            <tr><td><i>ID:</i></td><td>{group.id}</td></tr>
            <tr><td><i>Status:</i></td><td>{mute_status}</td></tr>
            <tr><td><i>Stream:</i></td><td>{group.stream_id}</td></tr>
            <tr><td><i>Clients:</i></td><td>{len(group.client_ids)}</td></tr>
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet("")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)

    def set_client(self, client: Client) -> None:
        """Display client properties.

        Args:
            client: Client to display.
        """
        status = "Connected" if client.connected else "Disconnected"
        html = f"""
            <h3>{client.name or client.host}</h3>
            <table cellpadding="4">
            <tr><td><i>ID:</i></td><td>{client.id}</td></tr>
            <tr><td><i>Host:</i></td><td>{client.host}</td></tr>
            <tr><td><i>Status:</i></td><td>{status}</td></tr>
            <tr><td><i>Volume:</i></td><td>{client.volume}%</td></tr>
            <tr><td><i>Muted:</i></td><td>{"Yes" if client.muted else "No"}</td></tr>
            <tr><td><i>Latency:</i></td><td>{client.latency}ms</td></tr>
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet("")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)

    def set_source(self, source: Source) -> None:
        """Display source properties.

        Args:
            source: Source to display.
        """
        status = "Playing" if source.is_playing else "Idle"
        html = f"""
            <h3>{source.name}</h3>
            <table cellpadding="4">
            <tr><td><i>ID:</i></td><td>{source.id}</td></tr>
            <tr><td><i>Status:</i></td><td>{status}</td></tr>
            <tr><td><i>Type:</i></td><td>{source.stream_type}</td></tr>
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet("")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop)
