"""Tests for styled dialog widgets."""

from unittest.mock import patch

from PySide6.QtWidgets import QDialog, QPushButton, QWidget
from pytestqt.qtbot import QtBot

from snapctrl.ui.widgets.dialogs import StyledInputDialog


class TestStyledInputDialog:
    """Test StyledInputDialog."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test dialog creation."""
        dialog = StyledInputDialog(None, "Test Title", "Enter name:")
        qtbot.addWidget(dialog)
        assert dialog.windowTitle() == "Test Title"

    def test_initial_text(self, qtbot: QtBot) -> None:
        """Test dialog with initial text."""
        dialog = StyledInputDialog(None, "Title", "Label:", text="initial value")
        qtbot.addWidget(dialog)
        assert dialog.text == "initial value"

    def test_text_property(self, qtbot: QtBot) -> None:
        """Test text property returns input content."""
        dialog = StyledInputDialog(None, "Title", "Label:", text="test")
        qtbot.addWidget(dialog)

        # Modify the input
        dialog._input.setText("modified")
        assert dialog.text == "modified"

    def test_accept_returns_text(self, qtbot: QtBot) -> None:
        """Test that accept closes with Accepted."""
        dialog = StyledInputDialog(None, "Title", "Label:", text="value")
        qtbot.addWidget(dialog)

        # Accept the dialog
        dialog.accept()
        assert dialog.result() == QDialog.DialogCode.Accepted

    def test_reject_returns_rejected(self, qtbot: QtBot) -> None:
        """Test that reject closes with Rejected."""
        dialog = StyledInputDialog(None, "Title", "Label:", text="value")
        qtbot.addWidget(dialog)

        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected

    def test_minimum_width(self, qtbot: QtBot) -> None:
        """Test dialog has minimum width."""
        dialog = StyledInputDialog(None, "Title", "Label:")
        qtbot.addWidget(dialog)
        assert dialog.minimumWidth() == 320

    def test_get_text_static_method_exists(self) -> None:
        """Test that get_text static method exists."""
        assert hasattr(StyledInputDialog, "get_text")
        assert callable(StyledInputDialog.get_text)

    def test_input_field_has_selection(self, qtbot: QtBot) -> None:
        """Test that initial text is selected."""
        dialog = StyledInputDialog(None, "Title", "Label:", text="test value")
        qtbot.addWidget(dialog)

        # Check that text is selected (hasSelectedText)
        assert dialog._input.hasSelectedText()

    def test_return_pressed_accepts(self, qtbot: QtBot) -> None:
        """Test that pressing enter in input accepts dialog."""
        dialog = StyledInputDialog(None, "Title", "Label:", text="test")
        qtbot.addWidget(dialog)

        # Simulate return pressed - should trigger accept
        with qtbot.waitSignal(dialog.accepted, timeout=1000):
            dialog._input.returnPressed.emit()

    def test_empty_initial_text(self, qtbot: QtBot) -> None:
        """Test dialog with empty initial text."""
        dialog = StyledInputDialog(None, "Title", "Label:")
        qtbot.addWidget(dialog)
        assert dialog.text == ""

    def test_dialog_has_buttons(self, qtbot: QtBot) -> None:
        """Test dialog has OK and Cancel buttons."""
        dialog = StyledInputDialog(None, "Title", "Label:")
        qtbot.addWidget(dialog)

        # Find buttons by iterating children
        buttons = dialog.findChildren(QPushButton)
        button_texts = [b.text() for b in buttons]
        assert "OK" in button_texts
        assert "Cancel" in button_texts

    def test_styling_applied(self, qtbot: QtBot) -> None:
        """Test that styling is applied to the dialog."""
        dialog = StyledInputDialog(None, "Title", "Label:")
        qtbot.addWidget(dialog)

        # Check that stylesheet was set
        assert dialog.styleSheet() != ""

    def test_with_parent_widget(self, qtbot: QtBot) -> None:
        """Test dialog with parent widget."""
        parent = QWidget()
        qtbot.addWidget(parent)

        dialog = StyledInputDialog(parent, "Title", "Label:")
        assert dialog.parent() == parent


class TestStyledInputDialogGetText:
    """Test get_text static method."""

    def test_get_text_accepted(self, qtbot: QtBot) -> None:
        """Test get_text returns text and True when accepted."""
        with patch.object(StyledInputDialog, "exec", return_value=QDialog.DialogCode.Accepted):
            text, ok = StyledInputDialog.get_text(None, "Title", "Label:", text="input")
            assert text == "input"
            assert ok is True

    def test_get_text_rejected(self, qtbot: QtBot) -> None:
        """Test get_text returns text and False when rejected."""
        with patch.object(StyledInputDialog, "exec", return_value=QDialog.DialogCode.Rejected):
            text, ok = StyledInputDialog.get_text(None, "Title", "Label:", text="input")
            assert text == "input"
            assert ok is False
