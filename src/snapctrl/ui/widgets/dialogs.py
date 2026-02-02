"""Themed dialog widgets for SnapCTRL.

Provides styled replacements for standard Qt dialogs that match
the application theme.

Usage:
    from snapctrl.ui.widgets.dialogs import StyledInputDialog

    name, ok = StyledInputDialog.get_text(parent, "Title", "Label:", text="default")
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from snapctrl.ui.theme import theme_manager
from snapctrl.ui.tokens import sizing, spacing, typography


class StyledInputDialog(QDialog):
    """A themed text input dialog replacing QInputDialog.

    Matches the application theme with styled input field, accent-colored
    OK button, and proper spacing using design tokens.

    Example:
        text, ok = StyledInputDialog.get_text(self, "Rename", "New name:", text="old")
    """

    def __init__(
        self,
        parent: QWidget | None,
        title: str,
        label: str,
        *,
        text: str = "",
    ) -> None:
        """Initialize the styled input dialog.

        Args:
            parent: Parent widget.
            title: Dialog window title.
            label: Prompt label above the input field.
            text: Initial text in the input field.
        """
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.CustomizeWindowHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setMinimumWidth(320)
        self._setup_ui(title, label, text)

    def _setup_ui(self, title: str, label: str, text: str) -> None:
        """Build the dialog UI.

        Args:
            title: Dialog title for the header label.
            label: Prompt label text.
            text: Initial input field text.
        """
        p = theme_manager.palette

        self.setStyleSheet(f"""
            StyledInputDialog {{
                background-color: {p.surface_elevated};
                border: 1px solid {p.border_selected};
                border-radius: {sizing.border_radius_lg}px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(spacing.md)
        layout.setContentsMargins(spacing.xl, spacing.lg, spacing.xl, spacing.lg)

        # Title
        title_label = QLabel(title)
        title_label.setStyleSheet(
            f"font-size: {typography.heading}pt;"
            f" font-weight: bold;"
            f" color: {p.text};"
            f" background: transparent;"
        )
        layout.addWidget(title_label)

        # Prompt
        prompt_label = QLabel(label)
        prompt_label.setStyleSheet(
            f"font-size: {typography.body}pt; color: {p.text_secondary}; background: transparent;"
        )
        layout.addWidget(prompt_label)

        # Input field
        self._input = QLineEdit(text)
        self._input.selectAll()
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {p.surface_dim};
                border: 1px solid {p.border};
                border-radius: {sizing.border_radius_md}px;
                padding: {spacing.sm}px;
                font-size: {typography.subtitle}pt;
                color: {p.text};
                selection-background-color: {p.accent};
            }}
            QLineEdit:focus {{
                border: 1px solid {p.accent};
            }}
        """)
        layout.addWidget(self._input)

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
                background: {p.warning};
            }}
        """)
        ok_btn.clicked.connect(self.accept)
        btn_row.addWidget(ok_btn)

        layout.addLayout(btn_row)

    @property
    def text(self) -> str:
        """Return the current input text."""
        return self._input.text()

    @staticmethod
    def get_text(
        parent: QWidget | None,
        title: str,
        label: str,
        *,
        text: str = "",
    ) -> tuple[str, bool]:
        """Show a styled input dialog and return (text, accepted).

        Drop-in replacement for QInputDialog.getText().

        Args:
            parent: Parent widget.
            title: Dialog window title.
            label: Prompt label above the input field.
            text: Initial text in the input field.

        Returns:
            Tuple of (entered text, True if accepted / False if cancelled).
        """
        dialog = StyledInputDialog(parent, title, label, text=text)
        result = dialog.exec()
        return dialog.text, result == QDialog.DialogCode.Accepted
