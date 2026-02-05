"""Extended tests for SnapclientManager covering stdout parsing, process events, etc."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QByteArray, QProcess

from snapctrl.core.snapclient_manager import (
    MAX_RESTART_ATTEMPTS,
    SnapclientManager,
    _do_process_check,
    invalidate_process_cache,
    is_snapclient_running,
)


@pytest.fixture(autouse=True)
def reset_cache() -> object:
    """Reset process cache before each test."""
    invalidate_process_cache()
    yield


class TestProcessCheck:
    """Test process check functionality."""

    def test_is_snapclient_running_uses_cache(self) -> None:
        """Test that repeated calls use cache."""
        with patch(
            "snapctrl.core.snapclient_manager._do_process_check", return_value=False
        ) as mock:
            # First call should check
            result1 = is_snapclient_running()
            # Second call should use cache
            result2 = is_snapclient_running()

            # Only one actual check
            assert mock.call_count == 1
            assert result1 is False
            assert result2 is False

    def test_invalidate_cache_forces_recheck(self) -> None:
        """Test that cache invalidation forces fresh check."""
        with patch(
            "snapctrl.core.snapclient_manager._do_process_check", return_value=False
        ) as mock:
            is_snapclient_running()
            invalidate_process_cache()
            is_snapclient_running()

            # Should have two checks after invalidation
            assert mock.call_count == 2

    def test_do_process_check_with_pgrep_not_found(self) -> None:
        """Test fallback when pgrep is not found."""
        with patch(
            "subprocess.run", side_effect=FileNotFoundError("pgrep not found")
        ) as mock_run:
            result = _do_process_check()
            # Should try pgrep, then ps fallback
            assert result is False


class TestStdoutParsing:
    """Test snapclient stdout parsing."""

    def _create_manager_with_process(self) -> tuple[SnapclientManager, MagicMock]:
        """Create a manager with a mock process."""
        mgr = SnapclientManager()
        mock_process = MagicMock(spec=QProcess)
        mgr._process = mock_process
        return mgr, mock_process

    def test_connected_to_line_sets_running(self) -> None:
        """Test that 'Connected to' line sets status to running."""
        mgr, mock_process = self._create_manager_with_process()
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        # Simulate stdout
        mock_process.readAllStandardOutput.return_value = QByteArray(
            b"[2024-01-01 12:00:00] Connected to 192.168.1.100"
        )

        mgr._on_stdout()

        assert "running" in statuses

    def test_host_id_detection_mac(self) -> None:
        """Test MAC address detection from stdout."""
        mgr, mock_process = self._create_manager_with_process()
        client_ids: list[str] = []
        mgr.client_id_detected.connect(client_ids.append)

        mock_process.readAllStandardOutput.return_value = QByteArray(
            b"[INFO] hostID: aa:bb:cc:dd:ee:ff\n"
        )

        mgr._on_stdout()

        assert len(client_ids) == 1
        assert client_ids[0] == "aa:bb:cc:dd:ee:ff"

    def test_host_id_detection_hostname(self) -> None:
        """Test hostname detection from stdout."""
        mgr, mock_process = self._create_manager_with_process()
        client_ids: list[str] = []
        mgr.client_id_detected.connect(client_ids.append)

        mock_process.readAllStandardOutput.return_value = QByteArray(
            b"[INFO] hostID: my-computer\n"
        )

        mgr._on_stdout()

        assert len(client_ids) == 1
        assert client_ids[0] == "my-computer"

    def test_invalid_host_id_rejected(self) -> None:
        """Test that invalid host IDs are rejected."""
        mgr, mock_process = self._create_manager_with_process()
        client_ids: list[str] = []
        mgr.client_id_detected.connect(client_ids.append)

        # Invalid format: starts with hyphen (invalid hostname label)
        mock_process.readAllStandardOutput.return_value = QByteArray(
            b"[INFO] hostID: -invalid-start\n"
        )

        mgr._on_stdout()

        assert len(client_ids) == 0

    def test_stdout_handles_invalid_utf8(self) -> None:
        """Test stdout handles invalid UTF-8 gracefully."""
        mgr, mock_process = self._create_manager_with_process()

        # Invalid UTF-8 bytes
        mock_process.readAllStandardOutput.return_value = QByteArray(
            b"[INFO] \xff\xfe Invalid bytes\n"
        )

        # Should not crash
        mgr._on_stdout()

    def test_stdout_with_no_process(self) -> None:
        """Test _on_stdout returns early when no process."""
        mgr = SnapclientManager()
        mgr._process = None
        mgr._on_stdout()  # Should not crash

    def test_multiline_stdout(self) -> None:
        """Test parsing multiple lines in one read."""
        mgr, mock_process = self._create_manager_with_process()
        statuses: list[str] = []
        client_ids: list[str] = []
        mgr.status_changed.connect(statuses.append)
        mgr.client_id_detected.connect(client_ids.append)

        mock_process.readAllStandardOutput.return_value = QByteArray(
            b"[INFO] hostID: ab:cd:ef:12:34:56\n"
            b"[INFO] Connected to 192.168.1.1\n"
        )

        mgr._on_stdout()

        assert "running" in statuses
        assert "ab:cd:ef:12:34:56" in client_ids


class TestProcessEvents:
    """Test QProcess event handlers."""

    def test_on_finished_crash_emits_error(self) -> None:
        """Test _on_finished with crash status emits error."""
        mgr = SnapclientManager()
        mgr._process = MagicMock()
        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        mgr._on_finished(1, QProcess.ExitStatus.CrashExit)

        assert len(errors) == 1
        assert "crashed" in errors[0]

    def test_on_finished_normal_exit_sets_stopped(self) -> None:
        """Test _on_finished with normal exit sets status to stopped."""
        mgr = SnapclientManager()
        mgr._process = MagicMock()
        mgr._auto_restart = False
        # Set status to something other than "stopped" first
        mgr._status = "running"
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        mgr._on_finished(0, QProcess.ExitStatus.NormalExit)

        assert "stopped" in statuses

    def test_on_finished_crash_with_auto_restart(self) -> None:
        """Test _on_finished with crash triggers auto-restart timer."""
        mgr = SnapclientManager()
        mgr._process = MagicMock()
        mgr._auto_restart = True

        with patch.object(mgr._restart_timer, "start") as mock_start:
            mgr._on_finished(1, QProcess.ExitStatus.CrashExit)
            mock_start.assert_called_once()

    def test_on_error_maps_error_types(self) -> None:
        """Test _on_error maps QProcess errors to messages."""
        mgr = SnapclientManager()
        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        mgr._on_error(QProcess.ProcessError.FailedToStart)

        assert len(errors) == 1
        assert "Failed to start" in errors[0]

    def test_on_error_sets_error_status(self) -> None:
        """Test _on_error sets status to error."""
        mgr = SnapclientManager()

        mgr._on_error(QProcess.ProcessError.Crashed)

        assert mgr.status == "error"


class TestAutoRestart:
    """Test auto-restart functionality."""

    def test_do_restart_without_binary(self) -> None:
        """Test _do_restart does nothing without binary path."""
        mgr = SnapclientManager()
        mgr._binary_path = None
        mgr._auto_restart = True

        # Should not crash
        mgr._do_restart()

    def test_do_restart_disabled(self) -> None:
        """Test _do_restart does nothing when disabled."""
        mgr = SnapclientManager()
        mgr._binary_path = "/usr/bin/snapclient"
        mgr._auto_restart = False

        # Should not crash or launch
        mgr._do_restart()

    def test_do_restart_exceeds_max_attempts(self) -> None:
        """Test _do_restart disables after max attempts."""
        mgr = SnapclientManager()
        mgr._binary_path = "/usr/bin/snapclient"
        mgr._auto_restart = True
        mgr._consecutive_failures = MAX_RESTART_ATTEMPTS

        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        mgr._do_restart()

        assert mgr._auto_restart is False
        assert len(errors) == 1
        assert "disabled" in errors[0]

    def test_do_restart_increments_failures(self) -> None:
        """Test _do_restart increments failure count."""
        mgr = SnapclientManager()
        mgr._binary_path = "/usr/bin/snapclient"
        mgr._auto_restart = True
        mgr._consecutive_failures = 0
        mgr._host = "localhost"
        mgr._port = 1704

        with patch.object(mgr, "_launch"):
            mgr._do_restart()

        assert mgr._consecutive_failures == 1


class TestExternalSnapclient:
    """Test external snapclient detection and handling."""

    def test_detect_external_when_running(self) -> None:
        """Test detect_external finds running snapclient."""
        mgr = SnapclientManager()

        with patch(
            "snapctrl.core.snapclient_manager.is_snapclient_running", return_value=True
        ):
            result = mgr.detect_external()

        assert result is True
        assert mgr.is_external is True
        assert mgr.status == "external"

    def test_detect_external_when_not_running(self) -> None:
        """Test detect_external returns False when not running."""
        mgr = SnapclientManager()

        with patch(
            "snapctrl.core.snapclient_manager.is_snapclient_running", return_value=False
        ):
            result = mgr.detect_external()

        assert result is False
        assert mgr.is_external is False

    def test_detect_external_skipped_when_managing_process(self) -> None:
        """Test detect_external returns False when already managing process."""
        mgr = SnapclientManager()
        mgr._process = MagicMock()

        result = mgr.detect_external()

        assert result is False

    def test_refresh_external_status_when_stopped(self) -> None:
        """Test refresh_external_status detects stopped external client."""
        mgr = SnapclientManager()
        mgr._is_external = True
        # Set status to something other than "stopped"
        mgr._status = "external"
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        with patch(
            "snapctrl.core.snapclient_manager.is_snapclient_running", return_value=False
        ):
            mgr.refresh_external_status()

        assert mgr.is_external is False
        assert "stopped" in statuses

    def test_refresh_external_status_when_not_external(self) -> None:
        """Test refresh_external_status does nothing when not external."""
        mgr = SnapclientManager()
        mgr._is_external = False

        mgr.refresh_external_status()  # Should not crash

    def test_check_external_status_stops_timer_when_managing(self) -> None:
        """Test _check_external_status stops timer when managing own process."""
        mgr = SnapclientManager()
        mgr._process = MagicMock()

        with patch.object(mgr._external_check_timer, "stop") as mock_stop:
            mgr._check_external_status()
            mock_stop.assert_called_once()

    def test_check_external_status_detects_new_external(self) -> None:
        """Test _check_external_status detects newly started external client."""
        mgr = SnapclientManager()
        mgr._is_external = False
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        with patch(
            "snapctrl.core.snapclient_manager.is_snapclient_running", return_value=True
        ):
            mgr._check_external_status()

        assert mgr.is_external is True
        assert "external" in statuses

    def test_check_external_status_detects_stopped_external(self) -> None:
        """Test _check_external_status detects stopped external client."""
        mgr = SnapclientManager()
        mgr._is_external = True
        # Set status to something other than "stopped"
        mgr._status = "external"
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        with patch(
            "snapctrl.core.snapclient_manager.is_snapclient_running", return_value=False
        ):
            mgr._check_external_status()

        assert mgr.is_external is False
        assert "stopped" in statuses


class TestStopBehavior:
    """Test stop behavior with running process."""

    def test_stop_external_client(self) -> None:
        """Test stop with external client just clears state."""
        mgr = SnapclientManager()
        mgr._is_external = True

        mgr.stop()

        assert mgr.is_external is False
        assert mgr.status == "stopped"

    def test_stop_terminates_process(self) -> None:
        """Test stop terminates running process."""
        mgr = SnapclientManager()
        mock_process = MagicMock()
        mock_process.state.return_value = QProcess.ProcessState.Running
        mock_process.waitForFinished.return_value = True
        mgr._process = mock_process

        mgr.stop()

        mock_process.terminate.assert_called()

    def test_stop_kills_unresponsive_process(self) -> None:
        """Test stop kills process that doesn't respond to terminate."""
        mgr = SnapclientManager()
        mock_process = MagicMock()
        mock_process.state.return_value = QProcess.ProcessState.Running
        mock_process.waitForFinished.return_value = False
        mgr._process = mock_process

        mgr.stop()

        mock_process.kill.assert_called()


class TestDetachBehavior:
    """Test detach behavior."""

    def test_detach_stops_timers(self) -> None:
        """Test detach stops all timers."""
        mgr = SnapclientManager()

        with (
            patch.object(mgr._restart_timer, "stop") as mock_restart_stop,
            patch.object(mgr._external_check_timer, "stop") as mock_external_stop,
        ):
            mgr.detach()

            mock_restart_stop.assert_called()
            mock_external_stop.assert_called()

    def test_detach_external_clears_state(self) -> None:
        """Test detach with external client clears state."""
        mgr = SnapclientManager()
        mgr._is_external = True
        # Set status to something other than "stopped"
        mgr._status = "external"
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        mgr.detach()

        assert mgr.is_external is False
        assert "stopped" in statuses

    def test_detach_restarts_in_detached_mode(self) -> None:
        """Test detach terminates managed process and restarts with startDetached."""
        mgr = SnapclientManager()
        mock_process = MagicMock()
        mock_process.state.return_value = QProcess.ProcessState.Running
        mgr._process = mock_process
        mgr._binary_path = "/usr/bin/snapclient"
        mgr._host = "localhost"
        mgr._port = 1704

        with patch.object(QProcess, "startDetached", return_value=True) as mock_detached:
            mgr.detach()

        # Verify managed process was terminated
        mock_process.terminate.assert_called_once()
        mock_process.waitForFinished.assert_called_once_with(1000)
        # Verify startDetached was called to restart independently
        mock_detached.assert_called_once()
        call_args = mock_detached.call_args
        assert call_args[0][0] == "/usr/bin/snapclient"
        assert "--host" in call_args[0][1]
        assert "localhost" in call_args[0][1]
        # Process should be cleaned up
        assert mgr._process is None


class TestLaunch:
    """Test launch behavior."""

    def test_launch_without_binary(self) -> None:
        """Test _launch returns early without binary path."""
        mgr = SnapclientManager()
        mgr._binary_path = None

        mgr._launch()  # Should not crash

    def test_launch_cleans_up_existing_process(self) -> None:
        """Test _launch cleans up existing process first."""
        mgr = SnapclientManager()
        mgr._binary_path = "/usr/bin/snapclient"
        mgr._host = "localhost"
        mgr._port = 1704

        old_process = MagicMock()
        mgr._process = old_process

        with patch.object(QProcess, "start"):
            mgr._launch()

        old_process.deleteLater.assert_called()

    def test_launch_stops_external_timer(self) -> None:
        """Test _launch stops external check timer."""
        mgr = SnapclientManager()
        mgr._binary_path = "/usr/bin/snapclient"
        mgr._host = "localhost"
        mgr._port = 1704

        with (
            patch.object(mgr._external_check_timer, "stop") as mock_stop,
            patch.object(QProcess, "start"),
        ):
            mgr._launch()

            mock_stop.assert_called()


class TestValidateBinary:
    """Test binary validation during start."""

    def test_start_emits_error_for_invalid_binary(self) -> None:
        """Test start emits error when binary validation fails."""
        mgr = SnapclientManager()
        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        with (
            patch(
                "snapctrl.core.snapclient_manager.is_snapclient_running",
                return_value=False,
            ),
            patch(
                "snapctrl.core.snapclient_manager.find_snapclient",
                return_value=Path("/usr/bin/snapclient"),
            ),
            patch(
                "snapctrl.core.snapclient_manager.validate_snapclient",
                return_value=(False, "Invalid binary"),
            ),
        ):
            mgr.start("192.168.1.100")

        assert mgr.status == "error"
        assert len(errors) == 1
        assert "Invalid" in errors[0]


class TestDoProcessCheck:
    """Test _do_process_check function."""

    def test_pgrep_success(self) -> None:
        """Test _do_process_check returns True when pgrep finds snapclient."""
        from snapctrl.core.snapclient_manager import _do_process_check

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            result = _do_process_check()

        assert result is True

    def test_pgrep_not_found_uses_ps_fallback(self) -> None:
        """Test _do_process_check uses ps fallback when pgrep fails."""
        from snapctrl.core.snapclient_manager import _do_process_check

        mock_ps_result = MagicMock()
        mock_ps_result.returncode = 0
        mock_ps_result.stdout = "bash\nzsh\nsnapclient\npython"

        def mock_run(args, **kwargs):
            if args[0] == "pgrep":
                raise FileNotFoundError("pgrep not found")
            return mock_ps_result

        with patch("subprocess.run", side_effect=mock_run):
            result = _do_process_check()

        assert result is True

    def test_ps_fallback_no_snapclient(self) -> None:
        """Test _do_process_check returns False when ps finds no snapclient."""
        from snapctrl.core.snapclient_manager import _do_process_check

        mock_ps_result = MagicMock()
        mock_ps_result.returncode = 0
        mock_ps_result.stdout = "bash\nzsh\npython"

        def mock_run(args, **kwargs):
            if args[0] == "pgrep":
                raise FileNotFoundError("pgrep not found")
            return mock_ps_result

        with patch("subprocess.run", side_effect=mock_run):
            result = _do_process_check()

        assert result is False


class TestIsSnapclientRunningCache:
    """Test is_snapclient_running caching behavior."""

    def test_cache_is_used(self) -> None:
        """Test that cached result is returned on repeated calls."""
        from snapctrl.core.snapclient_manager import (
            _process_check_cache,
            is_snapclient_running,
        )
        import time

        # Clear cache
        _process_check_cache.clear()

        with patch(
            "snapctrl.core.snapclient_manager._do_process_check",
            return_value=True,
        ) as mock_check:
            # First call - should call _do_process_check
            result1 = is_snapclient_running()

            # Second call - should use cache
            result2 = is_snapclient_running()

        assert result1 is True
        assert result2 is True
        # Should only call once due to caching
        mock_check.assert_called_once()
