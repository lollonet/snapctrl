"""Main application window with tri-pane layout.

Layout:
+----------------------------------+
| Sources | Groups   | Properties  |
| Panel   | Panel    | Panel       |
| (left)  | (center) | (right)     |
+----------------------------------+
"""

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import Signal, Slot
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QMainWindow, QPushButton, QSplitter, QWidget

from snapctrl.core.config import ConfigManager
from snapctrl.core.state import StateStore
from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source
from snapctrl.ui.panels.groups import GroupsPanel
from snapctrl.ui.panels.properties import PropertiesPanel
from snapctrl.ui.panels.sources import SourcesPanel
from snapctrl.ui.theme import theme_manager
from snapctrl.ui.tokens import sizing, spacing, typography

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from snapctrl.core.controller import Controller


class MainWindow(QMainWindow):
    """Main application window with tri-pane layout.

    The window is divided into three panels:
    - Left: SourcesPanel - list of audio sources
    - Center: GroupsPanel - scrollable list of group cards
    - Right: PropertiesPanel - details of selected item

    The window connects to a StateStore to reactively update when
    server state changes.

    Example:
        state = StateStore()
        controller = Controller(client, state)
        window = MainWindow(state, controller)
        window.show()
    """

    preferences_applied = Signal()

    def __init__(
        self,
        state_store: StateStore | None = None,
        controller: "Controller | None" = None,
        config: ConfigManager | None = None,
    ) -> None:
        """Initialize the main window.

        Args:
            state_store: Optional StateStore for reactive updates.
            controller: Optional Controller for wiring UI signals.
            config: Optional ConfigManager for preferences.
        """
        super().__init__()
        self._state = state_store
        self._controller: Controller | None = controller
        self._config = config
        self._selected_client_id: str | None = None  # Track selected client for properties updates
        self._ping_results: dict[str, float | None] = {}  # client_id -> RTT ms
        self._time_stats: dict[str, dict[str, object]] = {}  # client_id -> stats

        # Cache for status bar stylesheets to avoid repeated generation
        self._status_style_cache: dict[str, str] = {}
        self._snapclient_style_cache: dict[str, tuple[str, str]] = {}  # status -> (text, style)

        self._setup_ui()
        self._setup_style()
        self._connect_signals()

        # Connect theme changes to refresh styles
        theme_manager.theme_changed.connect(self._refresh_theme)

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("SnapCTRL")
        self.setMinimumSize(900, 600)

        # Create central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(spacing.xs, spacing.xs, spacing.xs, spacing.xs)
        main_layout.setSpacing(spacing.xs)

        # Create splitter for resizable panels
        splitter = QSplitter()

        # Create panels with fixed widths for side panels
        self._sources_panel = SourcesPanel()
        self._sources_panel.setMinimumWidth(sizing.panel_min_side)
        self._sources_panel.setMaximumWidth(250)

        self._groups_panel = GroupsPanel()

        self._properties_panel = PropertiesPanel()
        self._properties_panel.setMinimumWidth(200)
        self._properties_panel.setMaximumWidth(sizing.panel_max_side)

        # Add panels to splitter
        splitter.addWidget(self._sources_panel)
        splitter.addWidget(self._groups_panel)
        splitter.addWidget(self._properties_panel)

        # Set initial sizes (left: 180px, center: stretch, right: 220px)
        splitter.setSizes([180, 500, 220])

        # Set stretch factors so center panel expands
        splitter.setStretchFactor(0, 0)  # Sources: don't stretch
        splitter.setStretchFactor(1, 1)  # Groups: stretch
        splitter.setStretchFactor(2, 0)  # Properties: don't stretch

        # Add splitter to main layout
        main_layout.addWidget(splitter)

        # Server info label (left side of status bar)
        p = theme_manager.palette
        self._server_label = QLabel()
        self._server_label.setStyleSheet(
            f"color: {p.text_secondary};"
            f" padding: {spacing.xs}px {spacing.sm}px;"
            f" font-size: {typography.small}pt;"
        )
        self.statusBar().addWidget(self._server_label)

        # Connection status bar (right side)
        self._status_label = QLabel("Connecting...")
        self._status_label.setStyleSheet(
            f"background-color: {p.scrollbar}; color: {p.text};"
            f" padding: {spacing.xs}px {spacing.sm}px;"
            f" font-size: {typography.small}pt;"
            f" border-radius: {sizing.border_radius_sm}px;"
        )
        self.statusBar().addPermanentWidget(self._status_label)

        # Snapclient status label (hidden until enabled)
        self._snapclient_label = QLabel()
        self._snapclient_label.setStyleSheet(
            f"background-color: {p.scrollbar}; color: {p.text_disabled};"
            f" padding: {spacing.xs}px {spacing.sm}px;"
            f" font-size: {typography.small}pt;"
            f" border-radius: {sizing.border_radius_sm}px;"
        )
        self._snapclient_label.setVisible(False)
        self.statusBar().addPermanentWidget(self._snapclient_label)

        # Preferences gear button
        self._gear_btn = QPushButton("\u2699")
        self._gear_btn.setFixedSize(sizing.icon_md, sizing.icon_md)
        self._gear_btn.setFlat(True)
        self._gear_btn.setToolTip("Preferences")
        self._gear_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {typography.heading}pt;
                color: {p.text_secondary};
                border: none;
                background: transparent;
            }}
            QPushButton:hover {{
                color: {p.text};
            }}
        """)
        self._gear_btn.clicked.connect(self.open_preferences)
        self.statusBar().addPermanentWidget(self._gear_btn)

        self.statusBar().setStyleSheet(f"background-color: {p.background};")

    def _setup_style(self) -> None:
        """Set up basic styling."""
        p = theme_manager.palette
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {p.background};
            }}
            QWidget {{
                background-color: {p.surface};
                color: {p.text};
                font-family: {typography.font_family};
                font-size: {typography.subtitle}pt;
            }}
        """)

    def _refresh_theme(self) -> None:
        """Refresh all styles when theme changes."""
        p = theme_manager.palette

        # Clear style caches to force regeneration with new palette
        self._status_style_cache.clear()
        self._snapclient_style_cache.clear()

        # Re-apply main window stylesheet
        self._setup_style()

        # Re-apply server label style
        self._server_label.setStyleSheet(
            f"color: {p.text_secondary};"
            f" padding: {spacing.xs}px {spacing.sm}px;"
            f" font-size: {typography.small}pt;"
        )

        # Re-apply status bar styles
        self._status_label.setStyleSheet(
            f"background-color: {p.scrollbar}; color: {p.text};"
            f" padding: {spacing.xs}px {spacing.sm}px;"
            f" font-size: {typography.small}pt;"
            f" border-radius: {sizing.border_radius_sm}px;"
        )
        self._snapclient_label.setStyleSheet(
            f"background-color: {p.scrollbar}; color: {p.text_disabled};"
            f" padding: {spacing.xs}px {spacing.sm}px;"
            f" font-size: {typography.small}pt;"
            f" border-radius: {sizing.border_radius_sm}px;"
        )
        self._gear_btn.setStyleSheet(f"""
            QPushButton {{
                font-size: {typography.heading}pt;
                color: {p.text_secondary};
                border: none;
                background: transparent;
            }}
            QPushButton:hover {{
                color: {p.text};
            }}
        """)
        self.statusBar().setStyleSheet(f"background-color: {p.background};")

        # Refresh panels
        self._sources_panel.refresh_theme()
        self._groups_panel.refresh_theme()
        self._properties_panel.refresh_theme()

    def _connect_signals(self) -> None:
        """Connect StateStore signals to UI updates."""
        if not self._state:
            return

        # Connect sources
        self._state.sources_changed.connect(self._on_sources_changed)

        # Connect groups
        self._state.groups_changed.connect(self._on_groups_changed)

        # Connect clients
        self._state.clients_changed.connect(self._on_clients_changed)

        # Wire controller to group panel
        if self._controller:
            self._controller.connect_to_group_panel(self._groups_panel)

        # Connect source selection to controller
        self._sources_panel.source_selected.connect(self._on_source_selected)

        # Auto-select first group when a group is selected
        self._groups_panel.group_selected.connect(self._on_group_selected)

        # Note: volume/mute signals are connected in __main__.py to worker
        # Don't connect them here to avoid duplicate handlers

        # Connect client selection for properties panel
        self._groups_panel.client_selected.connect(self._on_client_selected)

    @Slot(str)
    def _on_source_selected(self, source_id: str) -> None:
        """Handle source selection from sources panel.

        Switches the currently selected group to the selected source.
        This emits the groups_panel.source_changed signal to trigger the change.

        Args:
            source_id: The source ID to switch to.
        """
        # Get the currently selected group
        group_id = self._groups_panel.selected_group_id

        # If no group is selected, default to the first group
        if not group_id:
            groups = self._state.groups if self._state else []
            if groups:
                group_id = groups[0].id
                self._groups_panel.set_selected_group(group_id)

        if group_id:
            # Emit through groups_panel to trigger the same handler as dropdown
            self._groups_panel.source_changed.emit(group_id, source_id)

    @Slot(str)
    def _on_group_selected(self, group_id: str) -> None:
        """Handle group selection from groups panel.

        Args:
            group_id: The group ID that was selected.
        """
        if self._state:
            group = self._state.get_group(group_id)
            if group:
                self._properties_panel.set_group(group)

    @Slot(str)
    def _on_client_selected(self, client_id: str) -> None:
        """Handle client selection from groups panel.

        Args:
            client_id: The client ID that was selected.
        """
        # Track selected client for state updates
        self._selected_client_id = client_id

        # Update visual selection
        self._groups_panel.set_selected_client(client_id)

        # Update properties panel with latency stats
        if self._state:
            client = self._state.get_client(client_id)
            if client:
                rtt = self._ping_results.get(client_id)
                stats = self._time_stats.get(client_id)
                self._properties_panel.set_client(
                    client,
                    network_rtt=rtt,
                    time_stats=stats,
                )

    @Slot(list)
    def _on_sources_changed(self, sources: list[Source]) -> None:
        """Handle sources change from StateStore.

        Args:
            sources: New list of sources.
        """
        self._sources_panel.set_sources(sources)

    @Slot(list)
    def _on_groups_changed(self, groups: list[Group]) -> None:
        """Handle groups change from StateStore.

        Args:
            groups: New list of groups.
        """
        sources = self._state.sources if self._state else []
        clients = self._state.clients if self._state else []

        # Group clients by their group ID
        clients_by_group: dict[str, list[Client]] = {}
        for client in clients:
            for group in groups:
                if client.id in group.client_ids:
                    if group.id not in clients_by_group:
                        clients_by_group[group.id] = []
                    clients_by_group[group.id].append(client)
                    break

        self._groups_panel.set_groups(groups, sources, clients_by_group)

        # Auto-select first group if none selected
        if groups and not self._groups_panel.selected_group_id:
            self._groups_panel.set_selected_group(groups[0].id)

    @Slot(list)
    def _on_clients_changed(self, clients: list[Client]) -> None:
        """Handle clients change from StateStore.

        Args:
            clients: New list of clients.
        """
        # Update existing group cards with new client data
        groups = self._state.groups if self._state else []
        sources = self._state.sources if self._state else []

        # Group clients by their group ID
        clients_by_group: dict[str, list[Client]] = {}
        for client in clients:
            for group in groups:
                if client.id in group.client_ids:
                    if group.id not in clients_by_group:
                        clients_by_group[group.id] = []
                    clients_by_group[group.id].append(client)
                    break

        self._groups_panel.set_groups(groups, sources, clients_by_group)

        # Update properties panel if selected client was updated
        if self._selected_client_id and self._state:
            client = self._state.get_client(self._selected_client_id)
            if client:
                rtt = self._ping_results.get(self._selected_client_id)
                stats = self._time_stats.get(self._selected_client_id)
                self._properties_panel.set_client(
                    client,
                    network_rtt=rtt,
                    time_stats=stats,
                )

    @property
    def sources_panel(self) -> SourcesPanel:
        """Return the sources panel."""
        return self._sources_panel

    @property
    def groups_panel(self) -> GroupsPanel:
        """Return the groups panel."""
        return self._groups_panel

    @property
    def properties_panel(self) -> PropertiesPanel:
        """Return the properties panel."""
        return self._properties_panel

    @property
    def config(self) -> ConfigManager | None:
        """Return the config manager."""
        return self._config

    @property
    def state_store(self) -> StateStore | None:
        """Return the state store."""
        return self._state

    def set_ping_results(self, results: dict[str, float | None]) -> None:
        """Set ping RTT results for clients.

        Args:
            results: Dict mapping client_id -> RTT in ms (or None).
        """
        self._ping_results = results
        # Update properties panel if a client is selected
        if self._selected_client_id and self._state:
            client = self._state.get_client(self._selected_client_id)
            if client:
                rtt = results.get(self._selected_client_id)
                stats = self._time_stats.get(self._selected_client_id)
                self._properties_panel.set_client(
                    client,
                    network_rtt=rtt,
                    time_stats=stats,
                )

    def set_time_stats(
        self,
        results: dict[str, dict[str, object]],
    ) -> None:
        """Set server-measured latency stats for clients.

        Args:
            results: Dict mapping client_id -> time stats dict.
        """
        self._time_stats = results
        # Update properties panel if a client is selected
        if self._selected_client_id and self._state:
            client = self._state.get_client(self._selected_client_id)
            if client:
                rtt = self._ping_results.get(self._selected_client_id)
                stats = results.get(self._selected_client_id)
                self._properties_panel.set_client(
                    client,
                    network_rtt=rtt,
                    time_stats=stats,
                )

    def set_connection_status(self, connected: bool, message: str = "") -> None:
        """Update the connection status indicator.

        Args:
            connected: Whether the server is connected.
            message: Optional status message.
        """
        cache_key = "connected" if connected else "disconnected"
        if cache_key not in self._status_style_cache:
            p = theme_manager.palette
            if connected:
                self._status_style_cache[cache_key] = (
                    f"background-color: {p.surface_success}; color: {p.success};"
                    f" padding: {spacing.xs}px {spacing.sm}px;"
                    f" font-size: {typography.small}pt;"
                    f" border-radius: {sizing.border_radius_sm}px;"
                )
            else:
                self._status_style_cache[cache_key] = (
                    f"background-color: {p.surface_error}; color: {p.error};"
                    f" padding: {spacing.xs}px {spacing.sm}px;"
                    f" font-size: {typography.small}pt;"
                    f" border-radius: {sizing.border_radius_sm}px;"
                )

        text = message or ("Connected" if connected else "Disconnected")
        self._status_label.setText(text)
        self._status_label.setStyleSheet(self._status_style_cache[cache_key])

    def set_snapclient_status(self, status: str) -> None:
        """Update the local snapclient status indicator.

        Args:
            status: One of "running", "starting", "stopped", "error", "disabled", "external".
        """
        if status == "disabled":
            self._snapclient_label.setVisible(False)
            return

        self._snapclient_label.setVisible(True)

        # Build style cache on demand
        if status not in self._snapclient_style_cache:
            p = theme_manager.palette
            base_style = (
                f" padding: {spacing.xs}px {spacing.sm}px;"
                f" font-size: {typography.small}pt;"
                f" border-radius: {sizing.border_radius_sm}px;"
            )
            status_config: dict[str, tuple[str, str, str]] = {
                "running": ("Local: Running", p.surface_success, p.success),
                "starting": ("Local: Starting...", p.scrollbar, p.warning),
                "stopped": ("Local: Stopped", p.scrollbar, p.text_disabled),
                "error": ("Local: Error", p.surface_error, p.error),
                "external": ("Local: External", p.surface_success, p.success),
            }
            if status not in status_config:
                logger.warning("Unknown snapclient status: %r", status)
            default = ("Local: Unknown", p.scrollbar, p.text_disabled)
            text, bg, fg = status_config.get(status, default)
            style = f"background-color: {bg}; color: {fg};{base_style}"
            self._snapclient_style_cache[status] = (text, style)

        text, style = self._snapclient_style_cache[status]
        self._snapclient_label.setText(text)
        self._snapclient_label.setStyleSheet(style)

    def set_server_info(self, host: str, port: int, hostname: str = "") -> None:
        """Store server host/port and display in status bar.

        Args:
            host: Server hostname or IP.
            port: Server port.
            hostname: Optional FQDN from mDNS discovery.
        """
        self._server_host = host
        self._server_port = port
        self._server_hostname = hostname

        # Update status bar label
        if hostname:
            self._server_label.setText(f"{hostname} ({host}):{port}")
        else:
            self._server_label.setText(f"{host}:{port}")

    def open_preferences(self) -> None:
        """Open the preferences dialog."""
        if not self._config:
            return
        from snapctrl.ui.widgets.preferences import PreferencesDialog  # noqa: PLC0415

        dialog = PreferencesDialog(self._config, parent=self)
        dialog.set_connection_info(
            getattr(self, "_server_host", ""),
            getattr(self, "_server_port", 1705),
            getattr(self, "_server_hostname", ""),
        )
        dialog.settings_changed.connect(self.preferences_applied.emit)
        dialog.open()

    def set_hide_to_tray(self, enabled: bool) -> None:
        """Enable or disable hiding to tray on close.

        When enabled, closing the window hides it to tray instead of quitting.

        Args:
            enabled: Whether to hide to tray on close.
        """
        self._hide_to_tray = enabled

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        """Handle window close event.

        If hide-to-tray is enabled, hides the window instead of closing.
        Otherwise, cleans up resources before closing.

        Args:
            event: The close event.
        """
        if getattr(self, "_hide_to_tray", False):
            event.ignore()
            self.hide()
        else:
            # Clean up SourcesPanel thread pool before closing
            self._sources_panel.cleanup()
            super().closeEvent(event)

    def toggle_visibility(self) -> None:
        """Toggle window visibility (for tray icon)."""
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()
            self.activateWindow()

    def get_ping_result(self, client_id: str) -> float | None:
        """Get ping RTT for a client.

        Args:
            client_id: The client ID.

        Returns:
            RTT in ms, or None if not available.
        """
        return self._ping_results.get(client_id)
