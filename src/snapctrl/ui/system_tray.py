"""System tray icon with show/hide, group status, now playing, and quick volume.

Provides a QSystemTrayIcon wrapper that integrates with StateStore
for live group/source status in the tray menu.

Usage:
    from snapctrl.ui.system_tray import SystemTrayManager

    tray = SystemTrayManager(window, state_store)
    tray.volume_changed.connect(on_group_volume_changed)
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING, cast

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QIcon, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSystemTrayIcon,
    QWidgetAction,
)

from snapctrl.core.snapclient_manager import SnapclientManager
from snapctrl.core.state import StateStore
from snapctrl.models.client import Client
from snapctrl.ui.theme import theme_manager
from snapctrl.ui.widgets.volume_slider import VolumeSlider

if TYPE_CHECKING:
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
    mute_changed = Signal(str, bool)  # group_id, muted
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

        # Cached target group for volume slider during transient states.
        # Prevents slider from disappearing during brief empty-state transitions
        # caused by signal timing during reconnection/state updates.
        self._cached_target_group: Group | None = None

        # Quick volume slider (embedded in menu)
        self._volume_slider: VolumeSlider | None = None

        # State fingerprint for skipping unnecessary menu rebuilds
        self._last_menu_fingerprint: str = ""

        # Flag to prevent timer spam when menu is open
        self._rebuild_pending: bool = False

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

    @staticmethod
    def _calc_avg_volume(client_ids: list[str], client_by_id: dict[str, Client]) -> int:
        """Calculate average volume for a group's connected clients.

        Only connected clients are included since disconnected clients
        aren't actively playing audio.

        Args:
            client_ids: List of client IDs in the group.
            client_by_id: Dict mapping client IDs to Client objects.

        Returns:
            Average volume (0-100), or 0 if no connected clients found.
        """
        total_vol = 0
        count = 0
        for cid in client_ids:
            client = client_by_id.get(cid)
            if client and client.connected:
                # Clamp volume to valid range (0-100) in case of corrupt data
                vol = max(0, min(100, client.volume))
                total_vol += vol
                count += 1
        # Use round() for proper averaging (74.5 -> 75, not 74)
        return round(total_vol / count) if count > 0 else 0

    def _compute_menu_fingerprint(self) -> str:
        """Compute a fingerprint of state relevant to the menu.

        This is used to skip menu rebuilds when nothing visible has changed.
        Returns a string hash of the relevant state components.

        Optimized: Uses pre-built client lookup dict to avoid O(n*m) filtering.
        """
        parts: list[str] = []

        # Connection state affects icon and tooltip
        parts.append(f"conn:{self._connected}")

        # Window visibility affects toggle label
        parts.append(f"vis:{self._window.isVisible()}")

        # Build client lookup once (O(n) instead of O(n*m))
        client_by_id = {c.id: c for c in self._state.clients}

        # Groups and their mute/volume/name/stream state
        for group in self._state.groups:
            avg_vol = self._calc_avg_volume(group.client_ids, client_by_id)
            parts.append(f"g:{group.id}:{group.name}:{group.muted}:{avg_vol}:{group.stream_id}")

        # Now playing - only include playing source (skip idle sources for perf)
        for source in self._state.sources:
            if source.is_playing:
                parts.append(f"s:{source.id}:{source.meta_title}:{source.meta_artist}")
                break  # Only show first playing source

        # Snapclient status
        if self._snapclient_mgr:
            parts.append(f"sc:{self._snapclient_mgr.status}")

        return "|".join(parts)

    def _rebuild_menu(self) -> None:
        """Rebuild the tray context menu from current state."""
        # Don't rebuild while the menu is open — destroying widgets mid-interaction
        # causes the slider to vanish and recreate, producing erratic volume jumps.
        if self._menu.isVisible():
            if not self._rebuild_pending:
                self._rebuild_pending = True
                self._rebuild_timer.start()  # Retry after menu closes
            return

        self._rebuild_pending = False

        # Check if rebuild is actually needed
        fingerprint = self._compute_menu_fingerprint()
        if fingerprint == self._last_menu_fingerprint:
            return  # Nothing changed, skip rebuild
        self._last_menu_fingerprint = fingerprint

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

        # Build client lookup once for all group entries
        client_by_id = {c.id: c for c in self._state.clients}

        # Group entries
        groups = self._state.groups
        if groups:
            for group in groups:
                self._add_group_entry(group, client_by_id)

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

        # Quick volume slider (reuse client_by_id from above)
        target_group = self._get_target_group()
        if target_group:
            self._menu.addSeparator()
            self._add_quick_volume(target_group, client_by_id)

        # Preferences and Quit
        self._menu.addSeparator()
        prefs_action = QAction("Preferences...", self._menu)
        prefs_action.triggered.connect(self.preferences_requested.emit)
        self._menu.addAction(prefs_action)

        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(self._on_quit)
        self._menu.addAction(quit_action)

    def _add_group_entry(self, group: Group, client_by_id: dict[str, Client]) -> None:
        """Add a clickable group entry to toggle mute.

        Args:
            group: The group to display.
            client_by_id: Dict mapping client IDs to Client objects.
        """
        avg_vol = self._calc_avg_volume(group.client_ids, client_by_id)

        # Visual distinction: muted shows "(muted)" instead of volume percentage
        label = f"🔇 {group.name} — (muted)" if group.muted else f"🔊 {group.name} — {avg_vol}%"

        action = QAction(label, self._menu)
        # Clicking toggles mute state - read current state at trigger time, not build time
        group_id = group.id
        action.triggered.connect(lambda *, gid=group_id: self._toggle_group_mute(gid))
        self._menu.addAction(action)

    def _toggle_group_mute(self, group_id: str) -> None:
        """Toggle mute state for a group, reading current state at trigger time.

        This reads the current mute state from StateStore when triggered, rather than
        capturing the state when the menu was built. This prevents stale state bugs
        where rapid clicks or external changes could cause incorrect toggle behavior.

        Args:
            group_id: The group to toggle.
        """
        group = self._state.get_group(group_id)
        if group:
            self.mute_changed.emit(group_id, not group.muted)
        else:
            logger.debug("Cannot toggle mute: group %s not found (may have been removed)", group_id)

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

    def _add_quick_volume(self, group: Group, client_by_id: dict[str, Client]) -> None:
        """Add an embedded volume slider for the target group.

        Args:
            group: The group to control.
            client_by_id: Pre-built client lookup dict (avoids duplicate creation).
        """
        # Calculate volume using the same helper as group entries (consistent rounding)
        avg_vol = self._calc_avg_volume(group.client_ids, client_by_id)

        # Don't show slider if no connected clients (volume would be 0/unknown)
        if avg_vol == 0 and not any(
            client_by_id.get(cid) and client_by_id[cid].connected for cid in group.client_ids
        ):
            return

        # Label
        label_action = QAction(f"Volume: {group.name}", self._menu)
        label_action.setEnabled(False)
        self._menu.addAction(label_action)

        # Embedded slider via QWidgetAction
        slider = VolumeSlider()
        slider.set_volume(avg_vol)
        slider.set_muted(group.muted)

        # Connect slider signals to emit with group_id
        group_id = group.id
        slider.volume_changed.connect(
            lambda vol: self.volume_changed.emit(group_id, vol)  # type: ignore[arg-type]
        )
        slider.mute_toggled.connect(
            lambda muted: self.mute_changed.emit(group_id, muted)  # type: ignore[arg-type]
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
            "external": "Local Client: External",
        }
        label = status_labels.get(status, f"Local Client: {status}")

        status_action = QAction(label, self._menu)
        status_action.setEnabled(False)
        self._menu.addAction(status_action)

        # Toggle action - external clients can't be stopped from here
        if self._snapclient_mgr.is_external:
            # External snapclient - no toggle action
            pass
        elif self._snapclient_mgr.is_running:
            toggle = QAction("Stop Local Client", self._menu)
            toggle.triggered.connect(self._on_stop_snapclient)
            self._menu.addAction(toggle)
        else:
            toggle = QAction("Start Local Client", self._menu)
            toggle.triggered.connect(self._on_start_snapclient)
            self._menu.addAction(toggle)

    def _on_stop_snapclient(self) -> None:
        """Stop the local snapclient."""
        if self._snapclient_mgr:
            logger.info("Stopping snapclient from tray")
            self._snapclient_mgr.stop()

    def _on_start_snapclient(self) -> None:
        """Start the local snapclient with configured host/port."""
        if self._snapclient_mgr and self._snapclient_host:
            logger.info(
                "Starting snapclient from tray: %s:%d",
                self._snapclient_host,
                self._snapclient_port,
            )
            try:
                self._snapclient_mgr.start(self._snapclient_host, self._snapclient_port)
            except ValueError as e:
                logger.error("Failed to start snapclient: %s", e)
                self._snapclient_mgr.error_occurred.emit(str(e))
        elif self._snapclient_mgr:
            # Host not configured
            msg = "No server configured for local snapclient"
            logger.warning(msg)
            self._snapclient_mgr.error_occurred.emit(msg)
        else:
            logger.warning("Snapclient manager not available")

    def _get_target_group(self) -> Group | None:
        """Get the group to control with the quick volume slider.

        Uses the selected group if set, otherwise the first group.
        Caches the result to maintain slider stability during state transitions.

        Returns:
            The target group, or None if no groups exist.
        """
        groups = self._state.groups

        # During transient empty states, return cached group if it's still valid
        if not groups:
            # Validate cache is still in state (handles race with connection_changed)
            if self._cached_target_group:
                if self._state.get_group(self._cached_target_group.id):
                    return self._cached_target_group
                self._cached_target_group = None
            return None

        # Try to use explicitly selected group
        if self._selected_group_id:
            group = self._state.get_group(self._selected_group_id)
            if group:
                self._cached_target_group = group
                return group

        # Fall back to first group and update cache for consistency
        self._cached_target_group = groups[0]
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

        # Invalidate cached group and menu fingerprint on disconnect
        if not connected:
            self._cached_target_group = None
            self._last_menu_fingerprint = ""  # Force menu rebuild on reconnect

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

    def cleanup(self) -> None:
        """Clean up resources before quitting.

        Stops timers and disconnects signals to prevent crashes during shutdown.
        Must be called before app.quit() or during aboutToQuit handling.
        """
        # Stop the rebuild timer to prevent callbacks during shutdown
        self._rebuild_timer.stop()

        # Disconnect state signals to prevent callbacks during destruction
        with contextlib.suppress(RuntimeError):
            self._state.groups_changed.disconnect(self._schedule_rebuild)
            self._state.sources_changed.disconnect(self._schedule_rebuild)
            self._state.clients_changed.disconnect(self._schedule_rebuild)
            self._state.connection_changed.disconnect(self._on_connection_changed)

        if self._snapclient_mgr:
            with contextlib.suppress(RuntimeError):
                self._snapclient_mgr.status_changed.disconnect(self._schedule_rebuild)

        # Clear menu to release widget references
        self._menu.clear()
        self._volume_slider = None
        self._cached_target_group = None
        self._last_menu_fingerprint = ""

    def _on_quit(self) -> None:
        """Quit the application.

        Shows snapclient confirmation dialog BEFORE initiating quit to avoid
        showing modal dialogs during Qt shutdown (which can cause SIGSEGV).
        """
        # Handle snapclient confirmation BEFORE quit (not in aboutToQuit)
        # Check window validity to avoid issues if event loop is in bad state
        if self._snapclient_mgr and self._snapclient_mgr.is_running:
            try:
                reply = QMessageBox.question(
                    self._window if self._window and self._window.isVisible() else None,
                    "Stop Local Client?",
                    "A local snapclient is running.\nStop it before quitting?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self._snapclient_mgr.stop()
                else:
                    # Detach so process survives app exit
                    self._snapclient_mgr.detach()
            except RuntimeError:
                # Widget deleted or event loop shutdown - just detach
                self._snapclient_mgr.detach()

        # Clean up tray resources before quitting
        self.cleanup()

        app = QApplication.instance()
        if app:
            app.quit()
