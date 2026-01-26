"""Main application window with tri-pane layout.

Layout:
+----------------------------------+
| Sources | Groups   | Properties  |
| Panel   | Panel    | Panel       |
| (left)  | (center) | (right)     |
+----------------------------------+
"""

from typing import TYPE_CHECKING

from PySide6.QtCore import Slot
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QSplitter, QWidget

from snapcast_mvp.core.state import StateStore
from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.source import Source
from snapcast_mvp.ui.panels.groups import GroupsPanel
from snapcast_mvp.ui.panels.properties import PropertiesPanel
from snapcast_mvp.ui.panels.sources import SourcesPanel

if TYPE_CHECKING:
    from snapcast_mvp.core.controller import Controller


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

    def __init__(
        self,
        state_store: StateStore | None = None,
        controller: "Controller | None" = None,
    ) -> None:
        """Initialize the main window.

        Args:
            state_store: Optional StateStore for reactive updates.
            controller: Optional Controller for wiring UI signals.
        """
        super().__init__()
        self._state = state_store
        self._controller: Controller | None = controller

        self._setup_ui()
        self._setup_style()
        self._connect_signals()

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        self.setWindowTitle("Snapcast MVP")
        self.setMinimumSize(900, 600)

        # Create central widget with main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(4)

        # Create splitter for resizable panels
        splitter = QSplitter()

        # Create panels
        self._sources_panel = SourcesPanel()
        self._groups_panel = GroupsPanel()
        self._properties_panel = PropertiesPanel()

        # Add panels to splitter
        splitter.addWidget(self._sources_panel)
        splitter.addWidget(self._groups_panel)
        splitter.addWidget(self._properties_panel)

        # Set initial sizes (left: 200px, center: 400px, right: 200px)
        splitter.setSizes([200, 400, 200])

        # Add splitter to main layout
        main_layout.addWidget(splitter)

    def _setup_style(self) -> None:
        """Set up basic styling."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #2d2d2d;
                color: #e0e0e0;
                font-size: 11pt;
            }
        """)

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

        # Connect client control signals to controller
        self._groups_panel.client_volume_changed.connect(self._on_client_volume_changed)
        self._groups_panel.client_mute_toggled.connect(self._on_client_mute_toggled)

    @Slot(str)
    async def _on_source_selected(self, source_id: str) -> None:
        """Handle source selection from sources panel.

        Switches the currently selected group to the selected source.

        Args:
            source_id: The source ID to switch to.
        """
        if not self._controller:
            return

        # Get the currently selected group
        group_id = self._groups_panel.selected_group_id

        # If no group is selected, default to the first group
        if not group_id:
            groups = self._state.groups if self._state else []
            if groups:
                group_id = groups[0].id
                self._groups_panel.set_selected_group(group_id)

        if group_id:
            await self._controller.on_group_source_changed(group_id, source_id)

    @Slot(str)
    def _on_group_selected(self, group_id: str) -> None:
        """Handle group selection from groups panel.

        Args:
            group_id: The group ID that was selected.
        """
        # Could update properties panel or status bar here
        pass

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

    @Slot(str, int)
    async def _on_client_volume_changed(self, client_id: str, volume: int) -> None:
        """Handle client volume change from group panel.

        Args:
            client_id: The client ID.
            volume: New volume value.
        """
        if self._controller:
            await self._controller.on_client_volume_changed(client_id, volume)

    @Slot(str, bool)
    async def _on_client_mute_toggled(self, client_id: str, muted: bool) -> None:
        """Handle client mute toggle from group panel.

        Args:
            client_id: The client ID.
            muted: New mute state.
        """
        if self._controller:
            await self._controller.on_client_mute_toggled(client_id, muted)

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
    def state_store(self) -> StateStore | None:
        """Return the state store."""
        return self._state
