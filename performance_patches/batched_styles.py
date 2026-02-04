"""Performance patch: Batched style updates."""

def _refresh_theme_batched(self) -> None:
    """Refresh all styles with batched updates to minimize recalculation."""
    p = theme_manager.palette  # Single palette lookup

    # Batch style changes by deferring updates
    with StyleBatchHelper([
        self._server_label,
        self._status_label,
        self._snapclient_label,
        self._gear_btn,
        self.statusBar()
    ]) as batch:

        # Main window (affects all children)
        self._setup_style()

        # Status bar components (batched)
        batch.set_style(self._server_label, f"""
            color: {p.text_secondary};
            padding: {spacing.xs}px {spacing.sm}px;
            font-size: {typography.small}pt;
        """)

        batch.set_style(self._status_label, f"""
            background-color: {p.scrollbar};
            color: {p.text};
            padding: {spacing.xs}px {spacing.sm}px;
            font-size: {typography.small}pt;
            border-radius: {sizing.border_radius_sm}px;
        """)

        batch.set_style(self._snapclient_label, f"""
            background-color: {p.scrollbar};
            color: {p.text_disabled};
            padding: {spacing.xs}px {spacing.sm}px;
            font-size: {typography.small}pt;
            border-radius: {sizing.border_radius_sm}px;
        """)

        batch.set_style(self._gear_btn, f"""
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

        batch.set_style(self.statusBar(), f"background-color: {p.background};")

    # Refresh panels after main window styles are applied
    self._sources_panel.refresh_theme()
    self._groups_panel.refresh_theme()
    self._properties_panel.refresh_theme()

class StyleBatchHelper:
    """Context manager to batch stylesheet updates."""

    def __init__(self, widgets: list):
        self.widgets = widgets
        self.updates = []

    def __enter__(self):
        # Block style updates
        for widget in self.widgets:
            widget.setUpdatesEnabled(False)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Apply all updates then enable updates
        for widget, style in self.updates:
            widget.setStyleSheet(style)
        for widget in self.widgets:
            widget.setUpdatesEnabled(True)

    def set_style(self, widget, style: str):
        self.updates.append((widget, style))