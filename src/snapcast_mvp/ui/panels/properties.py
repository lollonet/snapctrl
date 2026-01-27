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

# RTT color thresholds (milliseconds)
_RTT_GOOD_THRESHOLD = 50  # Green below this
_RTT_WARN_THRESHOLD = 100  # Yellow below this, red above
_RTT_PRECISION_THRESHOLD = 10  # Show decimal precision below this


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
        self._content.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
        self._content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.setStyleSheet("color: #606060; font-style: italic;")
        self._content.setWordWrap(True)
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
        self._content.setStyleSheet("color: #e0e0e0;")  # Ensure text is visible
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_client(self, client: Client, network_rtt: float | None = None) -> None:
        """Display client properties.

        Args:
            client: Client to display.
            network_rtt: Optional network RTT in milliseconds from ping.
        """
        status = "Connected" if client.connected else "Disconnected"
        status_color = "#80ff80" if client.connected else "#ff8080"

        # Build optional rows
        rows: list[str] = []
        rows.append(f"<tr><td><i>Host:</i></td><td>{client.host}</td></tr>")
        rows.append(
            f"<tr><td><i>Status:</i></td><td style='color: {status_color};'>{status}</td></tr>"
        )
        rows.append(f"<tr><td><i>Volume:</i></td><td>{client.volume}%</td></tr>")
        rows.append(f"<tr><td><i>Muted:</i></td><td>{'Yes' if client.muted else 'No'}</td></tr>")

        # Network RTT (ping) - prominently displayed
        if network_rtt is not None:
            if network_rtt < _RTT_PRECISION_THRESHOLD:
                rtt_str = f"{network_rtt:.1f}ms"
            else:
                rtt_str = f"{int(network_rtt)}ms"

            if network_rtt < _RTT_GOOD_THRESHOLD:
                rtt_color = "#80ff80"  # Green - good
            elif network_rtt < _RTT_WARN_THRESHOLD:
                rtt_color = "#ffff80"  # Yellow - warning
            else:
                rtt_color = "#ff8080"  # Red - high latency

            rows.append(
                f"<tr><td><i>Network RTT:</i></td>"
                f"<td style='color: {rtt_color};'>{rtt_str}</td></tr>"
            )
        elif client.connected:
            rows.append("<tr><td><i>Network RTT:</i></td><td>measuring...</td></tr>")

        # Latency offset (configured compensation)
        rows.append(f"<tr><td><i>Latency offset:</i></td><td>{client.display_latency}</td></tr>")

        # Last seen (timing info)
        if client.last_seen_sec > 0:
            rows.append(f"<tr><td><i>Last seen:</i></td><td>{client.last_seen_ago}</td></tr>")

        # System info
        if client.display_system:
            rows.append(f"<tr><td><i>System:</i></td><td>{client.display_system}</td></tr>")

        # Snapclient version
        if client.snapclient_version:
            rows.append(f"<tr><td><i>Snapclient:</i></td><td>{client.snapclient_version}</td></tr>")

        # MAC address
        if client.mac:
            rows.append(f"<tr><td><i>MAC:</i></td><td>{client.mac}</td></tr>")

        # Client ID (less prominent at bottom)
        rows.append(
            f"<tr><td><i>ID:</i></td><td style='font-size: 8pt;'>{client.id[:16]}...</td></tr>"
        )

        html = f"""
            <h3>{client.name or client.host}</h3>
            <table cellpadding="4">
            {"".join(rows)}
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet("color: #e0e0e0;")  # Ensure text is visible
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_source(self, source: Source) -> None:
        """Display source properties.

        Args:
            source: Source to display.
        """
        status = "Playing" if source.is_playing else "Idle"
        status_color = "#80ff80" if source.is_playing else "#808080"

        rows: list[str] = []
        rows.append(
            f"<tr><td><i>Status:</i></td><td style='color: {status_color};'>{status}</td></tr>"
        )

        # Stream type / scheme
        scheme = source.uri_scheme or source.stream_type
        if scheme:
            rows.append(f"<tr><td><i>Type:</i></td><td>{scheme}</td></tr>")

        # Codec
        if source.codec:
            rows.append(f"<tr><td><i>Codec:</i></td><td>{source.codec}</td></tr>")

        # Sample format
        fmt = source.display_format
        if fmt:
            rows.append(f"<tr><td><i>Format:</i></td><td>{fmt}</td></tr>")

        # Stream ID
        rows.append(f"<tr><td><i>ID:</i></td><td>{source.id}</td></tr>")

        html = f"""
            <h3>{source.name}</h3>
            <table cellpadding="4">
            {"".join(rows)}
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet("color: #e0e0e0;")  # Ensure text is visible
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
