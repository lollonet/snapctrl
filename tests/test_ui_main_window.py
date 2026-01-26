"""Tests for MainWindow."""

from pytestqt.qtbot import QtBot

from snapcast_mvp.ui.main_window import MainWindow


class TestMainWindowBasics:
    """Test MainWindow creation and layout."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test that main window can be created."""
        window = MainWindow()
        qtbot.addWidget(window)
        assert window.windowTitle() == "Snapcast MVP"
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


class TestMainWindowStyling:
    """Test MainWindow styling."""

    def test_has_stylesheet(self, qtbot: QtBot) -> None:
        """Test that main window has styling applied."""
        window = MainWindow()
        qtbot.addWidget(window)

        assert window.styleSheet() != ""
        assert "background-color" in window.styleSheet()
