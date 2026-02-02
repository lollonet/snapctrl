"""Properties panel - displays details of selected item."""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from snapctrl.core.ping import format_rtt, get_rtt_color
from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source
from snapctrl.ui.theme import theme_manager
from snapctrl.ui.tokens import spacing, typography

_JITTER_US_THRESHOLD = 0.001  # Below this, show as 0µs
_JITTER_PRECISION_THRESHOLD = 10  # Below this, show one decimal
_MS_TO_US = 1000  # Milliseconds to microseconds conversion


def _format_jitter(ms: float) -> str:
    """Format jitter value, showing microseconds when sub-millisecond."""
    if ms < _JITTER_US_THRESHOLD:
        return "0\u00b5s"
    if ms < 1:
        return f"{int(ms * _MS_TO_US)}\u00b5s"
    if ms < _JITTER_PRECISION_THRESHOLD:
        return f"{ms:.1f}ms"
    return f"{int(ms)}ms"


class PropertiesPanel(QWidget):
    """Right panel showing details of selected item.

    Displays properties of the currently selected group, client, or source.
    Shows nothing when nothing is selected.

    Example:
        panel = PropertiesPanel()
        panel.set_group(selected_group)
        panel.clear()
    """

    latency_changed = Signal(str, int)  # client_id, latency_ms

    def __init__(self) -> None:
        """Initialize the properties panel."""
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing.xs)

        # Header
        header = QLabel("Properties")
        header.setStyleSheet(f"font-weight: bold; font-size: {typography.title}pt;")
        layout.addWidget(header)

        # Content area (placeholder for now)
        p = theme_manager.palette
        self._content = QLabel("Select an item to see details")
        self._content.setTextFormat(Qt.TextFormat.RichText)  # Enable HTML rendering
        self._content.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._content.setStyleSheet(f"color: {p.text_disabled}; font-style: italic;")
        self._content.setWordWrap(True)
        layout.addWidget(self._content)

        # Latency control (shown for connected clients)
        self._latency_widget: QWidget | None = None
        self._latency_spinbox: QSpinBox | None = None
        self._current_client_id: str | None = None

        layout.addStretch()

    def clear(self) -> None:
        """Clear the properties panel."""
        p = theme_manager.palette
        self._content.setText("Select an item to see details")
        self._content.setStyleSheet(f"color: {p.text_disabled}; font-style: italic;")
        self._remove_latency_widget()

    def set_group(self, group: Group) -> None:
        """Display group properties.

        Args:
            group: Group to display.
        """
        self._remove_latency_widget()
        mute_status = "Muted" if group.muted else "Active"
        html = f"""
            <h3>{group.name}</h3>
            <table cellpadding="{spacing.xs}">
            <tr><td><i>ID:</i></td><td>{group.id}</td></tr>
            <tr><td><i>Status:</i></td><td>{mute_status}</td></tr>
            <tr><td><i>Stream:</i></td><td>{group.stream_id}</td></tr>
            <tr><td><i>Clients:</i></td><td>{len(group.client_ids)}</td></tr>
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet(f"color: {theme_manager.palette.text};")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_client(
        self,
        client: Client,
        network_rtt: float | None = None,
        time_stats: dict[str, Any] | None = None,
    ) -> None:
        """Display client properties.

        Args:
            client: Client to display.
            network_rtt: Optional network RTT in ms from ping (status bar fallback).
            time_stats: Optional server-measured latency stats from Client.GetTimeStats.
        """
        p = theme_manager.palette
        status = "Connected" if client.connected else "Disconnected"
        status_color = p.success if client.connected else p.error

        # Build optional rows
        rows: list[str] = []
        rows.append(f"<tr><td><i>Host:</i></td><td>{client.host}</td></tr>")
        rows.append(
            f"<tr><td><i>Status:</i></td><td style='color: {status_color};'>{status}</td></tr>"
        )
        rows.append(f"<tr><td><i>Volume:</i></td><td>{client.volume}%</td></tr>")
        rows.append(f"<tr><td><i>Muted:</i></td><td>{'Yes' if client.muted else 'No'}</td></tr>")

        # Server-side latency stats (preferred) or fallback to ping RTT
        samples = time_stats.get("samples", 0) if time_stats else 0
        if time_stats and isinstance(samples, (int, float)) and samples > 0:
            self._add_time_stats_rows(rows, time_stats)
        elif network_rtt is not None:
            rtt_str = format_rtt(network_rtt).replace("<", "&lt;")
            rtt_color = get_rtt_color(network_rtt)
            rows.append(
                f"<tr><td><i>Network RTT:</i></td>"
                f"<td style='color: {rtt_color};'>{rtt_str}</td></tr>"
            )
        elif client.connected:
            rows.append(
                f"<tr><td><i>Latency:</i></td>"
                f"<td style='color: {p.text_disabled};'>Measuring...</td></tr>"
            )

        # Latency offset — shown as interactive spinbox for connected clients,
        # read-only text for disconnected clients
        if not client.connected:
            rows.append(
                f"<tr><td><i>Latency offset:</i></td><td>{client.display_latency}</td></tr>"
            )

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
            f"<tr><td><i>ID:</i></td><td style='font-size: {typography.caption}pt;'>"
            f"{client.id[:16]}...</td></tr>"
        )

        html = f"""
            <h3>{client.name or client.host}</h3>
            <table cellpadding="{spacing.xs}">
            {"".join(rows)}
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet(f"color: {p.text};")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

        # Add interactive latency control for connected clients
        self._remove_latency_widget()
        if client.connected:
            self._current_client_id = client.id
            self._add_latency_widget(client.latency)

    @staticmethod
    def _add_time_stats_rows(
        rows: list[str],
        stats: dict[str, Any],
    ) -> None:
        """Add server-measured latency rows to the properties table."""
        try:
            median = float(stats.get("jitter_median_ms", 0.0))
            p95 = float(stats.get("jitter_p95_ms", 0.0))
            samples = int(stats.get("samples", 0))
        except (TypeError, ValueError):
            return

        median_color = get_rtt_color(median)
        p95_color = get_rtt_color(p95)
        median_str = _format_jitter(median)
        p95_str = _format_jitter(p95)

        rows.append(
            f"<tr><td><i>Jitter (server):</i></td>"
            f"<td style='color: {median_color};'>"
            f"{median_str}</td></tr>"
        )
        rows.append(
            f"<tr><td><i>Jitter P95:</i></td><td style='color: {p95_color};'>{p95_str}</td></tr>"
        )
        rows.append(f"<tr><td><i>Samples:</i></td><td>{samples}</td></tr>")

    def set_source(self, source: Source) -> None:
        """Display source properties.

        Args:
            source: Source to display.
        """
        self._remove_latency_widget()
        p = theme_manager.palette
        status = "Playing" if source.is_playing else "Idle"
        status_color = p.success if source.is_playing else p.text_disabled

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
            <table cellpadding="{spacing.xs}">
            {"".join(rows)}
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet(f"color: {p.text};")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def set_local_snapclient(
        self,
        status: str,
        binary_path: str = "",
        version: str = "",
        server_host: str = "",
        server_port: int = 1704,
    ) -> None:
        """Display local snapclient properties.

        Args:
            status: Current status ("running", "stopped", "starting", "error").
            binary_path: Path to snapclient binary.
            version: Snapclient version string.
            server_host: Connected server host.
            server_port: Connected server port.
        """
        self._remove_latency_widget()
        p = theme_manager.palette

        status_colors: dict[str, str] = {
            "running": p.success,
            "starting": p.warning,
            "stopped": p.text_disabled,
            "error": p.error,
        }
        status_color = status_colors.get(status, p.text_disabled)
        status_label = status.capitalize()

        rows: list[str] = []
        rows.append(
            f"<tr><td><i>Status:</i></td>"
            f"<td style='color: {status_color};'>{status_label}</td></tr>"
        )
        if binary_path:
            rows.append(f"<tr><td><i>Binary:</i></td><td>{binary_path}</td></tr>")
        if version:
            rows.append(f"<tr><td><i>Version:</i></td><td>{version}</td></tr>")
        if server_host:
            rows.append(f"<tr><td><i>Server:</i></td><td>{server_host}:{server_port}</td></tr>")

        html = f"""
            <h3>Local Snapclient</h3>
            <table cellpadding="{spacing.xs}">
            {"".join(rows)}
            </table>
        """
        self._content.setText(html)
        self._content.setStyleSheet(f"color: {p.text};")
        self._content.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)

    def _add_latency_widget(self, current_latency: int) -> None:
        """Add an interactive latency spinbox below the content.

        Args:
            current_latency: Current latency offset in ms.
        """
        p = theme_manager.palette
        self._latency_widget = QWidget()
        row = QHBoxLayout(self._latency_widget)
        row.setContentsMargins(spacing.xs, 0, spacing.xs, 0)

        label = QLabel("Latency offset:")
        label.setStyleSheet(f"color: {p.text}; font-style: italic;")
        row.addWidget(label)

        spinbox = QSpinBox()
        spinbox.setRange(-1000, 1000)
        spinbox.setSingleStep(10)
        spinbox.setSuffix(" ms")
        spinbox.setValue(current_latency)
        spinbox.editingFinished.connect(self._on_latency_editing_finished)
        row.addWidget(spinbox)

        row.addStretch()

        self._latency_spinbox = spinbox

        # Insert before the stretch (last item in layout)
        main_layout = self.layout()
        if main_layout is not None and isinstance(main_layout, QVBoxLayout):
            main_layout.insertWidget(main_layout.count() - 1, self._latency_widget)

    def _remove_latency_widget(self) -> None:
        """Remove the latency spinbox widget if present."""
        self._current_client_id = None
        if self._latency_widget is not None:
            self._latency_widget.setParent(None)  # type: ignore[call-overload]
            self._latency_widget = None
            self._latency_spinbox = None

    def _on_latency_editing_finished(self) -> None:
        """Emit latency_changed when the user finishes editing."""
        if self._current_client_id and self._latency_spinbox:
            self.latency_changed.emit(self._current_client_id, self._latency_spinbox.value())
