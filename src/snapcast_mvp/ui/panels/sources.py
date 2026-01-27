"""Sources panel - displays list of audio sources."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QWidget,
)

from snapcast_mvp.models.source import Source


class SourcesPanel(QWidget):
    """Left panel showing list of audio sources.

    Displays available audio sources (streams) with their playing status.
    Users can double-click to switch the currently selected group to that source.
    Shows details of the selected source below the list.

    Example:
        panel = SourcesPanel()
        panel.source_selected.connect(lambda sid: print(f"Selected: {sid}"))
        panel.set_sources([
            Source(id="1", name="MPD", status="playing", stream_type="flac"),
            Source(id="2", name="Spotify", status="idle", stream_type="ogg"),
        ])
    """

    # Signal emitted when a source is double-clicked (for switching groups)
    source_selected = Signal(str)  # source_id

    def __init__(self) -> None:
        """Initialize the sources panel."""
        super().__init__()
        self._sources: list[Source] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        # Header
        header = QLabel("Sources")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)

        # Source list
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget {
                background-color: #252525;
                border: none;
                padding: 4px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #404040;
            }
            QListWidget::item:hover {
                background-color: #353535;
            }
        """)
        self._list.itemDoubleClicked.connect(self._on_item_double_clicked)
        self._list.currentItemChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

        # Details section
        self._details_frame = QFrame()
        self._details_frame.setStyleSheet("""
            QFrame {
                background-color: #252525;
                border-radius: 4px;
                padding: 8px;
            }
            QLabel {
                color: #b0b0b0;
                font-size: 9pt;
            }
        """)
        details_layout = QVBoxLayout(self._details_frame)
        details_layout.setContentsMargins(8, 8, 8, 8)
        details_layout.setSpacing(4)

        self._detail_status = QLabel()
        self._detail_type = QLabel()
        self._detail_codec = QLabel()
        self._detail_format = QLabel()

        details_layout.addWidget(self._detail_status)
        details_layout.addWidget(self._detail_type)
        details_layout.addWidget(self._detail_codec)
        details_layout.addWidget(self._detail_format)

        layout.addWidget(self._details_frame)
        self._details_frame.setVisible(False)  # Hidden until selection

    def _on_item_double_clicked(self, item: QListWidgetItem) -> None:
        """Handle double-click on a source item.

        Args:
            item: The clicked list item.
        """
        source_id = item.data(Qt.ItemDataRole.UserRole)
        if source_id:
            self.source_selected.emit(source_id)

    def _on_selection_changed(
        self, current: QListWidgetItem | None, _previous: QListWidgetItem | None
    ) -> None:
        """Handle selection change to update details panel."""
        if not current:
            self._details_frame.setVisible(False)
            return

        source_id = current.data(Qt.ItemDataRole.UserRole)
        source = self._get_source_by_id(source_id)
        if source:
            self._update_details(source)
            self._details_frame.setVisible(True)
        else:
            self._details_frame.setVisible(False)

    def _get_source_by_id(self, source_id: str) -> Source | None:
        """Get source by ID from cached list."""
        for source in self._sources:
            if source.id == source_id:
                return source
        return None

    def _update_details(self, source: Source) -> None:
        """Update the details panel with source info."""
        # Status with color
        status = source.status.capitalize()
        if source.is_playing:
            self._detail_status.setText(f"Status: <span style='color: #80ff80;'>{status}</span>")
        else:
            self._detail_status.setText(f"Status: {status}")
        self._detail_status.setTextFormat(Qt.TextFormat.RichText)

        # Type (scheme)
        scheme = source.uri_scheme or source.stream_type or "unknown"
        self._detail_type.setText(f"Type: {scheme}")

        # Codec
        codec = source.display_codec
        self._detail_codec.setText(f"Codec: {codec}")

        # Sample format
        fmt = source.display_format
        if fmt:
            self._detail_format.setText(f"Format: {fmt}")
            self._detail_format.setVisible(True)
        else:
            self._detail_format.setVisible(False)

    def set_sources(self, sources: list[Source]) -> None:
        """Update the list of sources.

        Args:
            sources: List of Source objects to display.
        """
        # Cache sources for details lookup
        self._sources = sources

        # Remember current selection
        current_id = self.get_selected_source_id()

        self._list.clear()

        selected_item = None
        for source in sources:
            # Create item with icon indicator for playing status
            status_icon = "▶ " if source.is_playing else "  "
            item = QListWidgetItem(f"{status_icon}{source.name}")
            item.setData(Qt.ItemDataRole.UserRole, source.id)

            if source.is_playing:
                item.setForeground(Qt.GlobalColor.green)

            self._list.addItem(item)

            # Track previously selected item
            if source.id == current_id:
                selected_item = item

        # Restore selection
        if selected_item:
            self._list.setCurrentItem(selected_item)

    def clear_sources(self) -> None:
        """Clear all sources from the list."""
        self._list.clear()

    def get_selected_source_id(self) -> str | None:
        """Get the ID of the currently selected source.

        Returns:
            Source ID, or None if no selection.
        """
        item = self._list.currentItem()
        if item:
            return item.data(Qt.ItemDataRole.UserRole)
        return None
