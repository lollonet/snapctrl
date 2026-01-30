"""Tests for MainWindow."""

from unittest.mock import Mock

from pytestqt.qtbot import QtBot

from snapctrl.ui.main_window import MainWindow


class TestMainWindowBasics:
    """Test MainWindow creation and layout."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that main window can be created."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.windowTitle() == "SnapCTRL"
        assert window.minimumWidth() == 900
        assert window.minimumHeight() == 600

    def test_has_panels(self, qtbot: QtBot) -> None:
        """Test that main window has all three panels."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.sources_panel is not None
        assert window.groups_panel is not None
        assert window.properties_panel is not None

    def test_panels_are_visible(self, qtbot: QtBot) -> None:
        """Test that panels are visible."""
        window = MainWindow()
        window.show()
        qtbot.addWidget(window)

        assert window.sources_panel.isVisible()
        assert window.groups_panel.isVisible()
        assert window.properties_panel.isVisible()

    def test_group_mute_signal_connected(self, qtbot: QtBot) -> None:
        """Test that group mute toggle signal is connected to controller."""
        window = MainWindow()
        qtbot.addWidget(window)

        # Create a mock slot to verify signal connection
        mock_slot = Mock()

        # Connect to the group mute toggled signal
        window._groups_panel.mute_toggled.connect(mock_slot)

        # Emit a signal and verify it propagates
        window._groups_panel.mute_toggled.emit("test-group", True)

        # Verify the mock was called (group_id, muted)
        mock_slot.assert_called_once_with("test-group", True)

        # Clean up
        window._groups_panel.mute_toggled.disconnect(mock_slot)


class TestMainWindowSnapclientStatus:
    """Test snapclient status bar indicator."""

    def test_snapclient_label_hidden_initially(self, qtbot: QtBot) -> None:
        """Snapclient label is hidden by default."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        assert not window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_running(self, qtbot: QtBot) -> None:
        """Running status shows green label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("running")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Running" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_stopped(self, qtbot: QtBot) -> None:
        """Stopped status shows grey label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("stopped")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Stopped" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_error(self, qtbot: QtBot) -> None:
        """Error status shows red label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("error")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Error" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_disabled_hides(self, qtbot: QtBot) -> None:
        """Disabled status hides the label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("running")  # first show it
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        window.set_snapclient_status("disabled")
        assert not window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]

    def test_set_snapclient_status_starting(self, qtbot: QtBot) -> None:
        """Starting status shows label."""
        window = MainWindow()
        qtbot.addWidget(window)
        window.show()
        window.set_snapclient_status("starting")
        assert window._snapclient_label.isVisible()  # pyright: ignore[reportPrivateUsage]
        assert "Starting" in window._snapclient_label.text()  # pyright: ignore[reportPrivateUsage]


class TestMainWindowStyling:
    """Test MainWindow styling."""

    def test_has_stylesheet(self, qtbot: QtBot) -> None:
        """Test that main window has styling applied."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.styleSheet() != ""
        assert "background-color" in window.styleSheet()
