"""System tray icon with show/hide, group status, now playing, and quick volume.

Provides a QSystemTrayIcon wrapper that integrates with StateStore
for live group/source status in the tray menu.

Usage:
    from snapctrl.ui.system_tray import SystemTrayManager

    tray = SystemTrayManager(window, state_store)
    tray.volume_changed.connect(on_group_volume_changed)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QSystemTrayIcon,
    QWidgetAction,
)

from snapctrl.core.snapclient_manager import SnapclientManager
from snapctrl.core.state import StateStore
from snapctrl.ui.theme import theme_manager
from snapctrl.ui.widgets.volume_slider import VolumeSlider

if TYPE_CHECKING:
    from snapctrl.models.client import Client
    from snapctrl.models.group import Group
    from snapctrl.models.source import Source

logger = logging.getLogger(__name__)


class SystemTrayManager(QObject):
    """Manages the system tray icon and its context menu.

    Features:
    - Show/Hide window toggle (double-click or menu)
    - Group status with volume percentages
    - Now playing metadata from sources
    - Quick volume slider for the first (or selected) group
    - Quit action

    The menu rebuilds on state changes with 500ms debounce.

    Example:
        tray = SystemTrayManager(window, state_store)
        tray.volume_changed.connect(on_group_volume_changed)
        tray.show()
    """

    # Signals forwarded from the quick volume slider
    volume_changed = Signal(str, int)  # group_id, volume
    mute_all_changed = Signal(bool)  # True=mute all, False=unmute all
    preferences_requested = Signal()  # Open preferences dialog

    def __init__(
        self,
        window: QMainWindow,
        state_store: StateStore,
        icon: QIcon | None = None,
        snapclient_mgr: SnapclientManager | None = None,
    ) -> None:
        """Initialize the system tray manager.

        Args:
            window: The main application window.
            state_store: The state store for group/source data.
            icon: Optional icon for the tray. Falls back to app icon.
            snapclient_mgr: Optional local snapclient manager.
        """
        super().__init__()
        self._window = window
        self._state = state_store
        self._selected_group_id: str | None = None
        self._snapclient_mgr = snapclient_mgr
        self._snapclient_host = ""
        self._snapclient_port = 1704

        # Connection state for icon overlay
        self._connected = False

        # Quick volume slider (embedded in menu)
        self._volume_slider: VolumeSlider | None = None

        # Debounce timer for menu rebuild
        self._rebuild_timer = QTimer()
        self._rebuild_timer.setSingleShot(True)
        self._rebuild_timer.setInterval(500)
        self._rebuild_timer.timeout.connect(self._rebuild_menu)

        # Resolve icon
        if icon is None:
            raw_app = QApplication.instance()
            icon = cast(QApplication, raw_app).windowIcon() if raw_app is not None else QIcon()
        self._base_icon = icon

        # Create tray icon with connection status overlay
        self._tray = QSystemTrayIcon(self._build_status_icon())
        self._tray.setToolTip("SnapCTRL — Disconnected")
        self._tray.activated.connect(self._on_activated)

        # Build initial menu
        self._menu = QMenu()
        self._tray.setContextMenu(self._menu)
        self._rebuild_menu()

        # Connect state changes to debounced rebuild
        self._state.groups_changed.connect(self._schedule_rebuild)
        self._state.sources_changed.connect(self._schedule_rebuild)
        self._state.clients_changed.connect(self._schedule_rebuild)
        self._state.connection_changed.connect(self._on_connection_changed)

        # Connect snapclient status to rebuild
        if self._snapclient_mgr:
            self._snapclient_mgr.status_changed.connect(self._schedule_rebuild)

    @property
    def available(self) -> bool:
        """Return True if system tray is available on this platform."""
        return QSystemTrayIcon.isSystemTrayAvailable()

    @property
    def selected_group_id(self) -> str | None:
        """Return the currently selected group ID for quick volume."""
        return self._selected_group_id

    @selected_group_id.setter
    def selected_group_id(self, group_id: str | None) -> None:
        """Set which group the quick volume controls."""
        self._selected_group_id = group_id

    def set_snapclient_connection(self, host: str, port: int = 1704) -> None:
        """Set the host/port for snapclient start action.

        Args:
            host: Server hostname or IP.
            port: Server port.
        """
        self._snapclient_host = host
        self._snapclient_port = port

    def show(self) -> None:
        """Show the tray icon."""
        if self.available:
            self._tray.show()
            logger.info("System tray icon shown")
        else:
            logger.warning("System tray not available on this platform")

    def hide(self) -> None:
        """Hide the tray icon."""
        self._tray.hide()

    def _schedule_rebuild(self, *_args: object) -> None:
        """Schedule a debounced menu rebuild."""
        self._rebuild_timer.start()

    def _rebuild_menu(self) -> None:
        """Rebuild the tray context menu from current state."""
        self._menu.clear()
        self._volume_slider = None

        # Show/Hide toggle
        toggle_action = QAction(
            "Hide SnapCTRL" if self._window.isVisible() else "Show SnapCTRL",
            self._menu,
        )
        toggle_action.triggered.connect(self._toggle_window)
        self._menu.addAction(toggle_action)

        self._menu.addSeparator()

        # Group entries
        groups = self._state.groups
        clients = self._state.clients
        if groups:
            for group in groups:
                group_clients = [c for c in clients if c.id in group.client_ids]
                self._add_group_entry(group, group_clients)

            # Mute All / Unmute All
            mute_all = QAction("Mute All", self._menu)
            mute_all.triggered.connect(lambda: self.mute_all_changed.emit(True))
            self._menu.addAction(mute_all)

            unmute_all = QAction("Unmute All", self._menu)
            unmute_all.triggered.connect(lambda: self.mute_all_changed.emit(False))
            self._menu.addAction(unmute_all)

            self._menu.addSeparator()

        # Local Client
        if self._snapclient_mgr:
            self._add_local_client_section()
            self._menu.addSeparator()

        # Now Playing
        self._add_now_playing()

        # Quick volume slider
        target_group = self._get_target_group()
        if target_group:
            self._menu.addSeparator()
            self._add_quick_volume(target_group)

        # Preferences and Quit
        self._menu.addSeparator()
        prefs_action = QAction("Preferences...", self._menu)
        prefs_action.triggered.connect(self.preferences_requested.emit)
        self._menu.addAction(prefs_action)

        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

    def _add_group_entry(self, group: Group, clients: list[Client]) -> None:
        """Add a read-only group entry to the menu.

        Args:
            group: The group to display.
            clients: Clients in this group.
        """
        # Calculate average volume
        connected = [c for c in clients if c.connected]
        if connected:
            avg_vol = sum(c.volume for c in connected) // len(connected)
        elif clients:
            avg_vol = sum(c.volume for c in clients) // len(clients)
        else:
            avg_vol = 0

        mute_icon = "🔇" if group.muted else "🔊"
        label = f"{mute_icon} {group.name} — {avg_vol}%"
        action = QAction(label, self._menu)
        action.setEnabled(False)  # Read-only
        self._menu.addAction(action)

    def _add_now_playing(self) -> None:
        """Add now playing entry from source metadata."""
        sources = self._state.sources
        playing: list[Source] = [s for s in sources if s.is_playing and s.has_metadata]

        if not playing:
            return

        source = playing[0]
        title = source.meta_title or "Unknown"
        artist = source.meta_artist or ""
        label = f"♫ {title}"
        if artist:
            label += f" — {artist}"

        action = QAction(label, self._menu)
        action.setEnabled(False)
        self._menu.addAction(action)

    def _add_quick_volume(self, group: Group) -> None:
        """Add an embedded volume slider for the target group.

        Args:
            group: The group to control.
        """
        # Label
        label_action = QAction(f"Volume: {group.name}", self._menu)
        label_action.setEnabled(False)
        self._menu.addAction(label_action)

        # Embedded slider via QWidgetAction
        slider = VolumeSlider()

        # Calculate current volume from clients
        clients = self._state.clients
        group_clients = [c for c in clients if c.id in group.client_ids and c.connected]
        if group_clients:
            avg_vol = sum(c.volume for c in group_clients) // len(group_clients)
        else:
            avg_vol = 50
        slider.set_volume(avg_vol)
        slider.set_muted(group.muted)

        # Connect slider to emit volume_changed with group_id
        group_id = group.id
        slider.volume_changed.connect(
            lambda vol: self.volume_changed.emit(group_id, vol)  # type: ignore[arg-type]
        )

        widget_action = QWidgetAction(self._menu)
        widget_action.setDefaultWidget(slider)
        self._menu.addAction(widget_action)

        self._volume_slider = slider

    def _add_local_client_section(self) -> None:
        """Add local snapclient status and start/stop action to the menu."""
        if not self._snapclient_mgr:
            return

        status = self._snapclient_mgr.status
        status_labels = {
            "running": "Local Client: Running",
            "starting": "Local Client: Starting...",
            "stopped": "Local Client: Stopped",
            "error": "Local Client: Error",
        }
        label = status_labels.get(status, f"Local Client: {status}")

        status_action = QAction(label, self._menu)
        status_action.setEnabled(False)
        self._menu.addAction(status_action)

        # Toggle action
        if self._snapclient_mgr.is_running:
            toggle = QAction("Stop Local Client", self._menu)
            toggle.triggered.connect(self._snapclient_mgr.stop)
        else:
            toggle = QAction("Start Local Client", self._menu)
            toggle.triggered.connect(self._on_start_snapclient)
        self._menu.addAction(toggle)

    def _on_start_snapclient(self) -> None:
        """Start the local snapclient with configured host/port."""
        if self._snapclient_mgr and self._snapclient_host:
            try:
                self._snapclient_mgr.start(self._snapclient_host, self._snapclient_port)
            except ValueError as e:
                logger.error("Failed to start snapclient: %s", e)
                self._snapclient_mgr.error_occurred.emit(str(e))

    def _get_target_group(self) -> Group | None:
        """Get the group to control with the quick volume slider.

        Uses the selected group if set, otherwise the first group.

        Returns:
            The target group, or None if no groups exist.
        """
        groups = self._state.groups
        if not groups:
            return None

        if self._selected_group_id:
            group = self._state.get_group(self._selected_group_id)
            if group:
                return group

        return groups[0]

    def _build_status_icon(self) -> QIcon:
        """Build a tray icon with a connection status dot overlay.

        Returns:
            QIcon with green (connected) or red (disconnected) dot at bottom-right.
        """
        size = 64
        pixmap = self._base_icon.pixmap(size, size)
        if pixmap.isNull():
            return self._base_icon

        p = theme_manager.palette
        painter = QPainter(pixmap)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            dot_radius = 8
            dot_x = size - dot_radius * 2 - 2
            dot_y = size - dot_radius * 2 - 2
            color = QColor(p.success) if self._connected else QColor(p.error)

            painter.setPen(QPen(QColor(p.background), 2))
            painter.setBrush(QBrush(color))
            painter.drawEllipse(dot_x, dot_y, dot_radius * 2, dot_radius * 2)
        finally:
            painter.end()

        return QIcon(pixmap)

    def _on_connection_changed(self, connected: bool) -> None:
        """Update tray icon when connection state changes.

        Args:
            connected: True if connected, False if disconnected.
        """
        self._connected = connected
        self._tray.setIcon(self._build_status_icon())
        self._tray.setToolTip("SnapCTRL — Connected" if connected else "SnapCTRL — Disconnected")

    def _toggle_window(self) -> None:
        """Toggle main window visibility."""
        if self._window.isVisible():
            self._window.hide()
        else:
            self._window.show()
            self._window.raise_()
            self._window.activateWindow()

    def _on_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """Handle tray icon activation (click/double-click).

        Args:
            reason: The activation reason.
        """
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._toggle_window()

    def _on_quit(self) -> None:
        """Quit the application."""
        app = QApplication.instance()
        if app:
            app.quit()
