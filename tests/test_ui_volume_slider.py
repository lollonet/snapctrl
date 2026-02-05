"""Tests for VolumeSlider widget."""

from __future__ import annotations

from pytestqt.qtbot import QtBot

from snapctrl.ui.widgets.volume_slider import VolumeSlider


class TestVolumeSliderCreation:
    """Test volume slider creation."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test slider can be created."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)
        assert slider is not None

    def test_initial_volume(self, qtbot: QtBot) -> None:
        """Test slider starts at 50%."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)
        assert slider.volume == 50

    def test_initial_not_muted(self, qtbot: QtBot) -> None:
        """Test slider starts unmuted."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)
        assert slider.is_muted is False


class TestVolumeSliderSignals:
    """Test signal emissions."""

    def test_volume_changed_signal(self, qtbot: QtBot) -> None:
        """Test volume_changed signal is emitted."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        received: list[int] = []
        slider.volume_changed.connect(received.append)

        # Change slider value
        slider._slider.setValue(75)

        assert received == [75]

    def test_mute_toggled_signal(self, qtbot: QtBot) -> None:
        """Test mute_toggled signal is emitted."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        received: list[bool] = []
        slider.mute_toggled.connect(received.append)

        # Toggle mute
        slider._toggle_mute()

        assert received == [True]


class TestVolumeSliderSetVolume:
    """Test set_volume method."""

    def test_set_volume(self, qtbot: QtBot) -> None:
        """Test setting volume."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume(80)

        assert slider.volume == 80
        assert "80%" in slider._volume_label.text()

    def test_set_volume_no_signal(self, qtbot: QtBot) -> None:
        """Test set_volume doesn't emit signal."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        received: list[int] = []
        slider.volume_changed.connect(received.append)

        slider.set_volume(80)

        # Signal should not be emitted during set_volume
        assert received == []

    def test_set_volume_when_muted(self, qtbot: QtBot) -> None:
        """Test setting volume while muted."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_muted(True)
        slider.set_volume(80)

        # Slider should be at 0 (muted) but volume stored
        assert slider.volume == 0
        assert slider._volume_before_mute == 80


class TestVolumeSliderSetMuted:
    """Test set_muted method."""

    def test_set_muted_true(self, qtbot: QtBot) -> None:
        """Test muting."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume(75)
        slider.set_muted(True)

        assert slider.is_muted is True
        assert slider.volume == 0
        assert slider._volume_before_mute == 75
        assert "M" in slider._volume_label.text()

    def test_set_muted_false(self, qtbot: QtBot) -> None:
        """Test unmuting."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume(75)
        slider.set_muted(True)
        slider.set_muted(False)

        assert slider.is_muted is False
        assert slider.volume == 75
        assert "75%" in slider._volume_label.text()

    def test_set_muted_same_value(self, qtbot: QtBot) -> None:
        """Test setting muted to same value is no-op."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_muted(False)  # Already false
        assert slider.is_muted is False


class TestVolumeSliderToggleMute:
    """Test mute toggle functionality."""

    def test_toggle_mute_saves_volume(self, qtbot: QtBot) -> None:
        """Test toggle mute saves volume before muting."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume(75)
        slider._toggle_mute()

        assert slider._volume_before_mute == 75
        assert slider.volume == 0

    def test_toggle_mute_restores_volume(self, qtbot: QtBot) -> None:
        """Test toggle mute restores volume on unmute."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume(75)
        slider._toggle_mute()  # Mute
        slider._toggle_mute()  # Unmute

        assert slider.volume == 75

    def test_toggle_mute_updates_button(self, qtbot: QtBot) -> None:
        """Test toggle mute updates button icon."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider._toggle_mute()
        assert "🔇" in slider._mute_button.text()

        slider._toggle_mute()
        assert "🔊" in slider._mute_button.text()


class TestVolumeSliderSetVolumeAndMute:
    """Test set_volume_and_mute method."""

    def test_set_volume_and_mute_muted(self, qtbot: QtBot) -> None:
        """Test setting volume and mute together (muted)."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume_and_mute(80, True)

        assert slider.is_muted is True
        assert slider.volume == 0
        assert slider._volume_before_mute == 80

    def test_set_volume_and_mute_unmuted(self, qtbot: QtBot) -> None:
        """Test setting volume and mute together (unmuted)."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_volume_and_mute(80, False)

        assert slider.is_muted is False
        assert slider.volume == 80


class TestVolumeSliderRefreshTheme:
    """Test theme refresh."""

    def test_refresh_theme(self, qtbot: QtBot) -> None:
        """Test refresh_theme doesn't crash."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.refresh_theme()  # Should not crash


class TestVolumeSliderVolumeChangedWhenMuted:
    """Test volume change signal suppression when muted."""

    def test_no_signal_when_muted(self, qtbot: QtBot) -> None:
        """Test volume_changed not emitted when muted."""
        slider = VolumeSlider()
        qtbot.addWidget(slider)

        slider.set_muted(True)

        received: list[int] = []
        slider.volume_changed.connect(received.append)

        # Manually trigger the handler
        slider._on_volume_changed(50)

        # Should not emit when muted
        assert received == []
