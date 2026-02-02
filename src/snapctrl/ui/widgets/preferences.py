"""Preferences dialog for SnapCTRL.

Provides a tabbed dialog for configuring all application settings:
connection, appearance, local snapclient, and monitoring.

Usage:
    from snapctrl.ui.widgets.preferences import PreferencesDialog

    dialog = PreferencesDialog(config, parent=window)
    dialog.settings_changed.connect(on_settings_changed)
    dialog.exec()
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from snapctrl.core.config import ConfigManager
from snapctrl.ui.theme import DARK_PALETTE, LIGHT_PALETTE, theme_manager
from snapctrl.ui.tokens import sizing, spacing, typography


class PreferencesDialog(QDialog):
    """Tabbed preferences dialog for all application settings.

    Tabs: Connection, Appearance, Local Snapclient, Monitoring.

    Example:
        dialog = PreferencesDialog(config, parent=window)
        dialog.settings_changed.connect(lambda: print("Settings updated"))
        dialog.exec()
    """

    settings_changed = Signal()

    def __init__(
        self,
        config: ConfigManager,
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the preferences dialog.

        Args:
            config: ConfigManager for reading/writing settings.
            parent: Parent widget.
        """
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Preferences")
        self.setMinimumWidth(480)
        self.setMinimumHeight(360)
        self._setup_ui()
        self._load()

    def _setup_ui(self) -> None:
        """Build the dialog UI with tabs and buttons."""
        p = theme_manager.palette

        self.setStyleSheet(f"""
            PreferencesDialog {{
                background-color: {p.surface_elevated};
            }}
            QTabWidget::pane {{
                border: 1px solid {p.border};
                border-radius: {sizing.border_radius_md}px;
                background: {p.surface};
                padding: {spacing.sm}px;
            }}
            QTabBar::tab {{
                background: {p.surface_dim};
                border: 1px solid {p.border};
                padding: {spacing.sm}px {spacing.lg}px;
                margin-right: 2px;
                border-top-left-radius: {sizing.border_radius_md}px;
                border-top-right-radius: {sizing.border_radius_md}px;
                color: {p.text_secondary};
            }}
            QTabBar::tab:selected {{
                background: {p.surface};
                border-bottom-color: {p.surface};
                color: {p.text};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background: {p.surface_hover};
            }}
            QLabel {{
                background: transparent;
                color: {p.text};
            }}
            QCheckBox {{
                background: transparent;
                color: {p.text};
                spacing: {spacing.sm}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(spacing.md)
        layout.setContentsMargins(spacing.lg, spacing.lg, spacing.lg, spacing.lg)

        # Tab widget
        self._tabs = QTabWidget()
        self._tabs.addTab(self._create_connection_tab(), "Connection")
        self._tabs.addTab(self._create_appearance_tab(), "Appearance")
        self._tabs.addTab(self._create_snapclient_tab(), "Local Client")
        self._tabs.addTab(self._create_monitoring_tab(), "Monitoring")
        layout.addWidget(self._tabs)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(spacing.sm)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p.surface_hover};
                border: 1px solid {p.border};
                border-radius: {sizing.border_radius_md}px;
                padding: {spacing.sm}px {spacing.lg}px;
                color: {p.text};
                font-size: {typography.body}pt;
            }}
            QPushButton:hover {{
                background: {p.surface_selected};
            }}
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_btn = QPushButton("Apply")
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p.surface_hover};
                border: 1px solid {p.border};
                border-radius: {sizing.border_radius_md}px;
                padding: {spacing.sm}px {spacing.lg}px;
                color: {p.text};
                font-size: {typography.body}pt;
            }}
            QPushButton:hover {{
                background: {p.surface_selected};
            }}
        """)
        apply_btn.clicked.connect(self._apply)
        btn_row.addWidget(apply_btn)

        ok_btn = QPushButton("OK")
        ok_btn.setDefault(True)
        ok_btn.setStyleSheet(f"""
            QPushButton {{
                background: {p.accent};
                border: none;
                border-radius: {sizing.border_radius_md}px;
                padding: {spacing.sm}px {spacing.lg}px;
                color: #ffffff;
                font-size: {typography.body}pt;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: #CC7000;
            }}
        """)
        ok_btn.clicked.connect(self._ok)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    def _create_connection_tab(self) -> QWidget:
        """Create the Connection settings tab.

        Returns:
            Tab widget.
        """
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(spacing.md)
        form.setContentsMargins(spacing.md, spacing.md, spacing.md, spacing.md)

        # Server host (read-only info)
        self._conn_host = QLineEdit()
        self._conn_host.setReadOnly(True)
        self._conn_host.setPlaceholderText("Set via CLI or mDNS discovery")
        form.addRow("Server host:", self._conn_host)

        # Server port (read-only info)
        self._conn_port = QSpinBox()
        self._conn_port.setRange(1, 65535)
        self._conn_port.setReadOnly(True)
        form.addRow("Server port:", self._conn_port)

        # Auto-connect
        self._conn_auto = QCheckBox("Auto-connect on startup")
        form.addRow("", self._conn_auto)

        # Info label
        p = theme_manager.palette
        info = QLabel(
            "Server host/port are set via command line or mDNS.\n"
            "Restart the app to connect to a different server."
        )
        info.setStyleSheet(f"color: {p.text_disabled}; font-size: {typography.small}pt;")
        info.setWordWrap(True)
        form.addRow("", info)

        return tab

    def _create_appearance_tab(self) -> QWidget:
        """Create the Appearance settings tab.

        Returns:
            Tab widget.
        """
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(spacing.md)
        form.setContentsMargins(spacing.md, spacing.md, spacing.md, spacing.md)

        self._theme_combo = QComboBox()
        self._theme_combo.addItem("System", "system")
        self._theme_combo.addItem("Dark", "dark")
        self._theme_combo.addItem("Light", "light")
        self._theme_combo.currentIndexChanged.connect(self._on_theme_preview)
        form.addRow("Theme:", self._theme_combo)

        return tab

    def _create_snapclient_tab(self) -> QWidget:
        """Create the Local Snapclient settings tab.

        Returns:
            Tab widget.
        """
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(spacing.md)
        form.setContentsMargins(spacing.md, spacing.md, spacing.md, spacing.md)

        self._sc_enabled = QCheckBox("Enable local snapclient")
        form.addRow("", self._sc_enabled)

        # Binary path with browse button
        path_row = QHBoxLayout()
        self._sc_binary = QLineEdit()
        self._sc_binary.setPlaceholderText("Auto-detect")
        path_row.addWidget(self._sc_binary)

        browse_btn = QPushButton("Browse...")
        browse_btn.clicked.connect(self._browse_snapclient)
        path_row.addWidget(browse_btn)
        form.addRow("Binary path:", path_row)

        self._sc_auto_start = QCheckBox("Auto-start with app")
        form.addRow("", self._sc_auto_start)

        self._sc_extra_args = QLineEdit()
        self._sc_extra_args.setPlaceholderText("e.g. --soundcard default")
        form.addRow("Extra args:", self._sc_extra_args)

        return tab

    def _create_monitoring_tab(self) -> QWidget:
        """Create the Monitoring settings tab.

        Returns:
            Tab widget.
        """
        tab = QWidget()
        form = QFormLayout(tab)
        form.setSpacing(spacing.md)
        form.setContentsMargins(spacing.md, spacing.md, spacing.md, spacing.md)

        # Ping
        self._ping_interval = QSpinBox()
        self._ping_interval.setRange(5, 120)
        self._ping_interval.setSuffix(" s")
        form.addRow("Ping interval:", self._ping_interval)

        # Time stats
        self._time_stats_interval = QSpinBox()
        self._time_stats_interval.setRange(5, 120)
        self._time_stats_interval.setSuffix(" s")
        form.addRow("Jitter poll interval:", self._time_stats_interval)

        # MPD section header
        p = theme_manager.palette
        mpd_header = QLabel("MPD Integration")
        mpd_header.setStyleSheet(
            f"font-weight: bold; font-size: {typography.subtitle}pt;"
            f" color: {p.text}; margin-top: {spacing.md}px;"
        )
        form.addRow(mpd_header)

        self._mpd_host = QLineEdit()
        self._mpd_host.setPlaceholderText("Same as server")
        form.addRow("MPD host:", self._mpd_host)

        self._mpd_port = QSpinBox()
        self._mpd_port.setRange(1, 65535)
        form.addRow("MPD port:", self._mpd_port)

        self._mpd_poll = QSpinBox()
        self._mpd_poll.setRange(1, 30)
        self._mpd_poll.setSuffix(" s")
        form.addRow("MPD poll interval:", self._mpd_poll)

        return tab

    def _load(self) -> None:
        """Load current settings into widgets."""
        c = self._config

        # Connection (host/port set externally via set_connection_info)
        self._conn_auto.setChecked(c.get_auto_connect_profile() is not None)

        # Appearance
        theme = c.get_theme()
        idx = self._theme_combo.findData(theme)
        if idx >= 0:
            self._theme_combo.blockSignals(True)
            self._theme_combo.setCurrentIndex(idx)
            self._theme_combo.blockSignals(False)

        # Snapclient
        self._sc_enabled.setChecked(c.get_snapclient_enabled())
        self._sc_binary.setText(c.get_snapclient_binary_path())
        self._sc_auto_start.setChecked(c.get_snapclient_auto_start())
        self._sc_extra_args.setText(c.get_snapclient_extra_args())

        # Monitoring
        self._ping_interval.setValue(c.get_ping_interval())
        self._time_stats_interval.setValue(c.get_time_stats_interval())
        self._mpd_host.setText(c.get_mpd_host())
        self._mpd_port.setValue(c.get_mpd_port())
        self._mpd_poll.setValue(c.get_mpd_poll_interval())

    def _save(self) -> None:
        """Save widget values to config."""
        c = self._config

        # Appearance
        theme = self._theme_combo.currentData()
        if isinstance(theme, str):
            c.set_theme(theme)

        # Snapclient
        c.set_snapclient_enabled(self._sc_enabled.isChecked())
        c.set_snapclient_binary_path(self._sc_binary.text().strip())
        c.set_snapclient_auto_start(self._sc_auto_start.isChecked())
        c.set_snapclient_extra_args(self._sc_extra_args.text().strip())

        # Monitoring
        c.set_ping_interval(self._ping_interval.value())
        c.set_time_stats_interval(self._time_stats_interval.value())
        c.set_mpd_host(self._mpd_host.text().strip())
        c.set_mpd_port(self._mpd_port.value())
        c.set_mpd_poll_interval(self._mpd_poll.value())

        c.sync()

    def _apply(self) -> None:
        """Save settings and emit signal without closing."""
        self._save()
        self._apply_theme()
        self.settings_changed.emit()

    def _ok(self) -> None:
        """Save settings, emit signal, and close."""
        self._save()
        self._apply_theme()
        self.settings_changed.emit()
        self.accept()

    def _apply_theme(self) -> None:
        """Apply the selected theme immediately."""
        theme = self._theme_combo.currentData()
        if theme == "dark":
            theme_manager.apply_theme(DARK_PALETTE)
        elif theme == "light":
            theme_manager.apply_theme(LIGHT_PALETTE)
        else:
            theme_manager.apply_theme()  # system auto-detect

    def _on_theme_preview(self) -> None:
        """Preview theme change immediately when combo changes."""
        self._apply_theme()

    def _browse_snapclient(self) -> None:
        """Open file dialog to select snapclient binary."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select snapclient binary",
            self._sc_binary.text(),
        )
        if path:
            self._sc_binary.setText(path)

    def set_connection_info(self, host: str, port: int) -> None:
        """Set the current connection info (read-only display).

        Args:
            host: Current server host.
            port: Current server port.
        """
        self._conn_host.setText(host)
        self._conn_port.setValue(port)
