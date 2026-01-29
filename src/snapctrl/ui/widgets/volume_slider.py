"""Volume slider with mute button."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from snapctrl.ui.theme import theme_manager
from snapctrl.ui.tokens import sizing, spacing


class VolumeSlider(QWidget):
    """Volume slider with integrated mute button.

    Displays a slider (0-100%) and a mute toggle button.
    Emits signals when volume or mute state changes.

    Example:
        slider = VolumeSlider()
        slider.volume_changed.connect(lambda vol: print(f"Volume: {vol}"))
        slider.mute_toggled.connect(lambda muted: print(f"Muted: {muted}"))
        slider.set_volume(75)
    """

    volume_changed = Signal(int)  # New volume 0-100
    mute_toggled = Signal(bool)  # New mute state

    def __init__(self) -> None:
        """Initialize the volume slider."""
        super().__init__()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing.sm)

        # Volume percentage label
        self._volume_label = QLabel("50%")
        self._volume_label.setMinimumWidth(40)
        layout.addWidget(self._volume_label)

        # Volume slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(0)
        self._slider.setMaximum(100)
        self._slider.setValue(50)
        self._slider.setMinimumWidth(120)
        self._slider.valueChanged.connect(self._on_volume_changed)
        layout.addWidget(self._slider)

        # Mute button
        p = theme_manager.palette
        self._mute_button = QPushButton("🔊")
        self._mute_button.setFixedSize(sizing.control_button, sizing.control_button)
        self._mute_button.setFlat(True)
        self._mute_button.setStyleSheet(f"""
            QPushButton {{
                border: none;
                font-size: 16px;
            }}
            QPushButton:hover {{
                background-color: {p.surface_hover};
                border-radius: {sizing.border_radius_md}px;
            }}
        """)
        self._mute_button.clicked.connect(self._toggle_mute)
        layout.addWidget(self._mute_button)

        # State
        self._muted = False
        self._volume_before_mute = 50

    def _on_volume_changed(self, value: int) -> None:
        """Handle slider value change.

        Args:
            value: New volume value 0-100.
        """
        self._volume_label.setText(f"{value}%")
        if not self._muted:
            self.volume_changed.emit(value)

    def _toggle_mute(self) -> None:
        """Toggle mute state."""
        self._muted = not self._muted

        if self._muted:
            # Save current volume and mute
            self._volume_before_mute = self._slider.value()
            self._slider.blockSignals(True)
            self._slider.setValue(0)
            self._slider.blockSignals(False)
            self._volume_label.setText("M")
            self._mute_button.setText("🔇")
        else:
            # Restore volume and unmute
            self._slider.blockSignals(True)
            self._slider.setValue(self._volume_before_mute)
            self._slider.blockSignals(False)
            self._volume_label.setText(f"{self._volume_before_mute}%")
            self._mute_button.setText("🔊")

        # Only emit mute_toggled - the handler should use the stored volume
        self.mute_toggled.emit(self._muted)

    @property
    def volume(self) -> int:
        """Return current volume."""
        return self._slider.value()

    @property
    def is_muted(self) -> bool:
        """Return mute state."""
        return self._muted

    def set_volume(self, volume: int) -> None:
        """Set the volume (0-100).

        Args:
            volume: Volume value.
        """
        self._slider.blockSignals(True)
        self._slider.setValue(volume)
        self._volume_label.setText(f"{volume}%")
        self._slider.blockSignals(False)

        # Always update _volume_before_mute so unmuting restores to the new volume
        if not self._muted:
            self._volume_before_mute = volume
        else:
            # When muted, still update the stored volume so unmute uses new value
            self._volume_before_mute = volume
            # Reset slider to 0 to maintain muted state
            self._slider.blockSignals(True)
            self._slider.setValue(0)
            self._slider.blockSignals(False)

    def set_muted(self, muted: bool) -> None:
        """Set the mute state without emitting signals (for external updates).

        Args:
            muted: Whether to mute.
        """
        if self._muted == muted:
            return

        self._muted = muted

        if muted:
            self._volume_before_mute = self._slider.value()
            self._slider.blockSignals(True)
            self._slider.setValue(0)
            self._slider.blockSignals(False)
            self._volume_label.setText("M")
            self._mute_button.setText("🔇")
        else:
            self._slider.blockSignals(True)
            self._slider.setValue(self._volume_before_mute)
            self._slider.blockSignals(False)
            self._volume_label.setText(f"{self._volume_before_mute}%")
            self._mute_button.setText("🔊")

    def set_volume_and_mute(self, volume: int, muted: bool) -> None:
        """Set both volume and mute state atomically without emitting signals.

        Used for external state updates (e.g., from server).

        Args:
            volume: Volume value.
            muted: Whether to mute.
        """
        self._muted = muted
        self._volume_before_mute = volume

        if muted:
            self._slider.blockSignals(True)
            self._slider.setValue(0)
            self._slider.blockSignals(False)
            self._volume_label.setText("M")
            self._mute_button.setText("🔇")
        else:
            self._slider.blockSignals(True)
            self._slider.setValue(volume)
            self._slider.blockSignals(False)
            self._volume_label.setText(f"{volume}%")
            self._mute_button.setText("🔊")
