"""Tests for PreferencesDialog."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from PySide6.QtWidgets import QDialog
from pytestqt.qtbot import QtBot

from snapctrl.core.config import ConfigManager
from snapctrl.ui.widgets.preferences import PreferencesDialog


@pytest.fixture
def mock_config() -> ConfigManager:
    """Create a ConfigManager for testing."""
    return ConfigManager("SnapcastMVPTest", "TestPrefs")


class TestPreferencesDialogCreation:
    """Test dialog creation."""

    def test_creation(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test dialog can be created."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Preferences"

    def test_minimum_size(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test dialog has minimum size for readability."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 560
        assert dialog.minimumHeight() == 400

    def test_has_tabs(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test dialog has all tabs."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        tabs = dialog._tabs
        assert tabs.count() == 4
        assert tabs.tabText(0) == "Connection"
        assert tabs.tabText(1) == "Appearance"
        assert tabs.tabText(2) == "Local Client"
        assert tabs.tabText(3) == "Monitoring"

    def test_has_settings_changed_signal(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test dialog has settings_changed signal."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)
        assert hasattr(dialog, "settings_changed")


class TestConnectionTab:
    """Test Connection tab."""

    def test_connection_fields_exist(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test connection tab has required fields."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_conn_host")
        assert hasattr(dialog, "_conn_port")
        assert hasattr(dialog, "_conn_auto")

    def test_connection_fields_readonly(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test host/port fields are read-only."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._conn_host.isReadOnly()
        assert dialog._conn_port.isReadOnly()

    def test_set_connection_info(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test setting connection info."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        dialog.set_connection_info("192.168.1.100", 1705)
        assert dialog._conn_host.text() == "192.168.1.100"
        assert dialog._conn_port.value() == 1705

    def test_set_connection_info_with_hostname(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test setting connection info with hostname."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        dialog.set_connection_info("192.168.1.100", 1705, "server.local")
        assert "server.local" in dialog._conn_host.text()
        assert "192.168.1.100" in dialog._conn_host.text()


class TestAppearanceTab:
    """Test Appearance tab."""

    def test_theme_combo_exists(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test theme combo box exists."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_theme_combo")

    def test_theme_options(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test theme combo has correct options."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        combo = dialog._theme_combo
        assert combo.count() == 3

        # Check items by data
        themes = [combo.itemData(i) for i in range(combo.count())]
        assert "system" in themes
        assert "dark" in themes
        assert "light" in themes

    def test_theme_preview_on_change(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test theme preview is triggered on combo change."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        with patch.object(dialog, "_apply_theme") as mock_apply:
            dialog._theme_combo.setCurrentIndex(1)  # Change to different theme
            mock_apply.assert_called()


class TestSnapclientTab:
    """Test Local Snapclient tab."""

    def test_snapclient_fields_exist(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test snapclient tab has required fields."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_sc_enabled")
        assert hasattr(dialog, "_sc_binary")
        assert hasattr(dialog, "_sc_auto_start")
        assert hasattr(dialog, "_sc_extra_args")

    def test_browse_button_opens_file_dialog(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test browse button opens file dialog."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        with patch(
            "snapctrl.ui.widgets.preferences.QFileDialog.getOpenFileName",
            return_value=("/usr/bin/snapclient", ""),
        ):
            dialog._browse_snapclient()
            assert dialog._sc_binary.text() == "/usr/bin/snapclient"

    def test_browse_button_empty_on_cancel(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test browse button handles cancel."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)
        dialog._sc_binary.setText("original")

        with patch(
            "snapctrl.ui.widgets.preferences.QFileDialog.getOpenFileName",
            return_value=("", ""),
        ):
            dialog._browse_snapclient()
            assert dialog._sc_binary.text() == "original"


class TestMonitoringTab:
    """Test Monitoring tab."""

    def test_monitoring_fields_exist(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test monitoring tab has required fields."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert hasattr(dialog, "_ping_interval")
        assert hasattr(dialog, "_time_stats_interval")
        assert hasattr(dialog, "_mpd_host")
        assert hasattr(dialog, "_mpd_port")
        assert hasattr(dialog, "_mpd_poll")

    def test_ping_interval_range(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test ping interval has valid range."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._ping_interval.minimum() == 5
        assert dialog._ping_interval.maximum() == 120

    def test_mpd_port_range(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test MPD port has valid range."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        assert dialog._mpd_port.minimum() == 1
        assert dialog._mpd_port.maximum() == 65535


class TestLoadSave:
    """Test loading and saving settings."""

    def test_load_settings(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test settings are loaded from config."""
        # Set some values in config
        mock_config.set_theme("dark")
        mock_config.set_snapclient_enabled(True)
        mock_config.set_ping_interval(30)

        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Check values were loaded
        idx = dialog._theme_combo.currentIndex()
        assert dialog._theme_combo.itemData(idx) == "dark"
        assert dialog._sc_enabled.isChecked() is True
        assert dialog._ping_interval.value() == 30

    def test_save_settings(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test settings are saved to config."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Modify widgets
        dialog._conn_auto.setChecked(True)
        dialog._sc_enabled.setChecked(True)
        dialog._sc_binary.setText("/custom/snapclient")
        dialog._ping_interval.setValue(60)

        # Save
        dialog._save()

        # Verify config
        assert mock_config.get_auto_connect_enabled() is True
        assert mock_config.get_snapclient_enabled() is True
        assert mock_config.get_snapclient_binary_path() == "/custom/snapclient"
        assert mock_config.get_ping_interval() == 60

    def test_save_strips_whitespace(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test save strips whitespace from text fields."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        dialog._sc_binary.setText("  /path/with/spaces  ")
        dialog._sc_extra_args.setText("  --arg1  ")
        dialog._mpd_host.setText("  host.local  ")

        dialog._save()

        assert mock_config.get_snapclient_binary_path() == "/path/with/spaces"
        assert mock_config.get_snapclient_extra_args() == "--arg1"
        assert mock_config.get_mpd_host() == "host.local"


class TestDialogActions:
    """Test dialog buttons and actions."""

    def test_ok_saves_and_closes(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test OK button saves settings and closes dialog."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        received: list[bool] = []
        dialog.settings_changed.connect(lambda: received.append(True))

        with patch.object(dialog, "_save") as mock_save:
            dialog._ok()
            mock_save.assert_called_once()

        assert len(received) == 1
        assert dialog.result() == QDialog.DialogCode.Accepted

    def test_apply_saves_without_closing(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test Apply button saves without closing."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        received: list[bool] = []
        dialog.settings_changed.connect(lambda: received.append(True))

        with patch.object(dialog, "_save") as mock_save:
            dialog._apply()
            mock_save.assert_called_once()

        assert len(received) == 1

    def test_cancel_reverts_theme(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test Cancel reverts theme preview."""
        mock_config.set_theme("dark")
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Verify original theme was stored
        assert dialog._original_theme == "dark"

        # Change theme
        dialog._theme_combo.setCurrentIndex(2)  # Light

        # Cancel should revert
        with patch("snapctrl.ui.widgets.preferences.theme_manager") as mock_tm:
            dialog.reject()
            # Should call apply_theme with DARK_PALETTE
            mock_tm.apply_theme.assert_called()

    def test_cancel_reverts_system_theme(
        self, qtbot: QtBot, mock_config: ConfigManager
    ) -> None:
        """Test Cancel reverts system theme correctly."""
        mock_config.set_theme("system")
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Change to dark
        dialog._theme_combo.setCurrentIndex(1)

        with patch("snapctrl.ui.widgets.preferences.theme_manager") as mock_tm:
            dialog.reject()
            # Should call apply_theme with no args (system)
            mock_tm.apply_theme.assert_called()


class TestThemeApplication:
    """Test theme application."""

    def test_apply_dark_theme(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test applying dark theme."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Set to dark
        idx = dialog._theme_combo.findData("dark")
        dialog._theme_combo.setCurrentIndex(idx)

        with patch("snapctrl.ui.widgets.preferences.theme_manager") as mock_tm:
            dialog._apply_theme()
            mock_tm.apply_theme.assert_called()

    def test_apply_light_theme(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test applying light theme."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Set to light
        idx = dialog._theme_combo.findData("light")
        dialog._theme_combo.setCurrentIndex(idx)

        with patch("snapctrl.ui.widgets.preferences.theme_manager") as mock_tm:
            dialog._apply_theme()
            mock_tm.apply_theme.assert_called()

    def test_apply_system_theme(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test applying system theme."""
        dialog = PreferencesDialog(mock_config)
        qtbot.addWidget(dialog)

        # Set to system
        idx = dialog._theme_combo.findData("system")
        dialog._theme_combo.setCurrentIndex(idx)

        with patch("snapctrl.ui.widgets.preferences.theme_manager") as mock_tm:
            dialog._apply_theme()
            mock_tm.apply_theme.assert_called()


class TestParentWidget:
    """Test dialog with parent widget."""

    def test_with_parent(self, qtbot: QtBot, mock_config: ConfigManager) -> None:
        """Test dialog with parent widget."""
        from PySide6.QtWidgets import QWidget

        parent = QWidget()
        qtbot.addWidget(parent)

        dialog = PreferencesDialog(mock_config, parent=parent)
        assert dialog.parent() == parent
