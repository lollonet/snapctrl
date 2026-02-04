"""Tests for SnapclientManager (QProcess-based subprocess manager)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from PySide6.QtCore import QProcess

from snapctrl.core.snapclient_manager import (
    BACKOFF_MULTIPLIER,
    INITIAL_BACKOFF_MS,
    KILL_TIMEOUT_MS,
    MAX_BACKOFF_MS,
    TERMINATE_TIMEOUT_MS,
    SnapclientManager,
)


@pytest.fixture(autouse=True)
def mock_system_snapclient_check() -> object:
    """Disable system-wide snapclient check for all tests."""
    with patch("snapctrl.core.snapclient_manager.is_snapclient_running", return_value=False):
        yield


class TestSnapclientManagerInit:
    """Test initialization and defaults."""

    def test_default_status(self) -> None:
        """Manager starts with 'stopped' status."""
        mgr = SnapclientManager()
        assert mgr.status == "stopped"

    def test_not_running_initially(self) -> None:
        """Manager is not running initially."""
        mgr = SnapclientManager()
        assert mgr.is_running is False


class TestSnapclientManagerConfig:
    """Test configuration methods."""

    def test_set_configured_binary_path(self) -> None:
        """Can set a custom binary path."""
        mgr = SnapclientManager()
        mgr.set_configured_binary_path("/opt/snapclient")
        # Verify via internal state (test-only access)
        assert mgr._configured_binary_path == "/opt/snapclient"  # pyright: ignore[reportPrivateUsage]

    def test_set_configured_binary_path_none(self) -> None:
        """Can clear custom binary path."""
        mgr = SnapclientManager()
        mgr.set_configured_binary_path("/opt/snapclient")
        mgr.set_configured_binary_path(None)
        assert mgr._configured_binary_path is None  # pyright: ignore[reportPrivateUsage]

    def test_set_extra_args(self) -> None:
        """Can set extra CLI arguments."""
        mgr = SnapclientManager()
        mgr.set_extra_args(["--latency", "100"])
        assert mgr._extra_args == ["--latency", "100"]  # pyright: ignore[reportPrivateUsage]

    def test_set_extra_args_copies_list(self) -> None:
        """Extra args are copied, not referenced."""
        mgr = SnapclientManager()
        args = ["--latency", "100"]
        mgr.set_extra_args(args)
        args.append("--mixer")
        assert len(mgr._extra_args) == 2  # pyright: ignore[reportPrivateUsage]

    def test_set_extra_args_rejects_blocked_flags(self) -> None:
        """Blocked flags like --host are rejected."""
        mgr = SnapclientManager()
        with pytest.raises(ValueError, match="Blocked arguments"):
            mgr.set_extra_args(["--host", "evil"])

    def test_set_extra_args_rejects_logsink(self) -> None:
        """--logsink is a blocked flag."""
        mgr = SnapclientManager()
        with pytest.raises(ValueError, match="Blocked arguments"):
            mgr.set_extra_args(["--logsink", "/tmp/exfil"])

    def test_set_host_id(self) -> None:
        """Can set custom host ID."""
        mgr = SnapclientManager()
        mgr.set_host_id("my-custom-id")
        assert mgr._host_id == "my-custom-id"  # pyright: ignore[reportPrivateUsage]

    def test_enable_auto_restart(self) -> None:
        """Can toggle auto-restart."""
        mgr = SnapclientManager()
        mgr.enable_auto_restart(False)
        assert mgr._auto_restart is False  # pyright: ignore[reportPrivateUsage]
        mgr.enable_auto_restart(True)
        assert mgr._auto_restart is True  # pyright: ignore[reportPrivateUsage]


class TestSnapclientManagerStartValidation:
    """Test start() input validation."""

    def test_start_rejects_empty_host(self) -> None:
        """Start raises ValueError for empty host."""
        mgr = SnapclientManager()
        with pytest.raises(ValueError, match="Host must not be empty"):
            mgr.start("")

    def test_start_rejects_whitespace_host(self) -> None:
        """Start raises ValueError for whitespace-only host."""
        mgr = SnapclientManager()
        with pytest.raises(ValueError, match="Host must not be empty"):
            mgr.start("   ")

    def test_start_rejects_invalid_port(self) -> None:
        """Start raises ValueError for out-of-range port."""
        mgr = SnapclientManager()
        with pytest.raises(ValueError, match="Port must be"):
            mgr.start("192.168.1.1", port=0)

    def test_start_rejects_port_too_high(self) -> None:
        """Start raises ValueError for port > 65535."""
        mgr = SnapclientManager()
        with pytest.raises(ValueError, match="Port must be"):
            mgr.start("192.168.1.1", port=70000)


class TestSnapclientManagerStart:
    """Test start behavior."""

    def test_start_adopts_external_snapclient_when_running(self) -> None:
        """Start adopts external snapclient instead of blocking."""
        mgr = SnapclientManager()
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        with patch("snapctrl.core.snapclient_manager.is_snapclient_running", return_value=True):
            mgr.start("192.168.1.100")

        # Should adopt external snapclient
        assert mgr.status == "external"
        assert mgr.is_external is True
        assert "external" in statuses

    def test_start_emits_error_when_binary_not_found(self) -> None:
        """Start emits error_occurred when binary not found."""
        mgr = SnapclientManager()
        errors: list[str] = []
        mgr.error_occurred.connect(errors.append)

        with patch("snapctrl.core.snapclient_manager.find_snapclient", return_value=None):
            mgr.start("192.168.1.100")

        assert mgr.status == "error"
        assert len(errors) == 1
        assert "not found" in errors[0]

    def test_start_sets_starting_status(self) -> None:
        """Start transitions to 'starting' status when binary found."""
        mgr = SnapclientManager()
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        fake_binary = Path("/usr/bin/snapclient")

        with (
            patch("snapctrl.core.snapclient_manager.find_snapclient", return_value=fake_binary),
            patch(
                "snapctrl.core.snapclient_manager.validate_snapclient",
                return_value=(True, "0.31.0"),
            ),
            patch.object(QProcess, "start") as mock_start,
            patch.object(QProcess, "state", return_value=QProcess.ProcessState.NotRunning),
        ):
            mgr.start("192.168.1.100")
            assert "starting" in statuses
            mock_start.assert_called_once()

    def test_start_resets_backoff(self) -> None:
        """Start resets the backoff timer."""
        mgr = SnapclientManager()
        mgr._backoff_ms = 16000  # pyright: ignore[reportPrivateUsage]

        with (
            patch(
                "snapctrl.core.snapclient_manager.find_snapclient",
                return_value=Path("/usr/bin/snapclient"),
            ),
            patch.object(QProcess, "start"),
            patch.object(QProcess, "state", return_value=QProcess.ProcessState.NotRunning),
        ):
            mgr.start("192.168.1.100")
            assert mgr._backoff_ms == INITIAL_BACKOFF_MS  # pyright: ignore[reportPrivateUsage]


class TestSnapclientManagerBuildArgs:
    """Test CLI argument building."""

    def _setup_mgr(
        self,
        host: str = "localhost",
        port: int = 1704,
        host_id: str = "",
        extra_args: list[str] | None = None,
    ) -> SnapclientManager:
        """Create a manager with host/port set for arg building."""
        mgr = SnapclientManager()
        mgr._host = host  # pyright: ignore[reportPrivateUsage]
        mgr._port = port  # pyright: ignore[reportPrivateUsage]
        if host_id:
            mgr.set_host_id(host_id)
        if extra_args:
            mgr.set_extra_args(extra_args)
        return mgr

    def test_basic_args(self) -> None:
        """Builds basic host/port args."""
        mgr = self._setup_mgr(host="192.168.1.100")
        args = mgr._build_args()  # pyright: ignore[reportPrivateUsage]
        assert "--host" in args
        assert "192.168.1.100" in args
        assert "--port" in args
        assert "1704" in args

    def test_includes_logsink(self) -> None:
        """Always includes --logsink stdout for output parsing."""
        mgr = self._setup_mgr()
        args = mgr._build_args()  # pyright: ignore[reportPrivateUsage]
        assert "--logsink" in args
        assert "stdout" in args

    def test_includes_host_id(self) -> None:
        """Includes --hostID when set."""
        mgr = self._setup_mgr(host_id="custom-id")
        args = mgr._build_args()  # pyright: ignore[reportPrivateUsage]
        assert "--hostID" in args
        assert "custom-id" in args

    def test_no_host_id_when_empty(self) -> None:
        """Omits --hostID when not set."""
        mgr = self._setup_mgr()
        args = mgr._build_args()  # pyright: ignore[reportPrivateUsage]
        assert "--hostID" not in args

    def test_includes_extra_args(self) -> None:
        """Appends extra args at the end."""
        mgr = self._setup_mgr(extra_args=["--latency", "100"])
        args = mgr._build_args()  # pyright: ignore[reportPrivateUsage]
        assert "--latency" in args
        assert "100" in args


class TestSnapclientManagerStop:
    """Test stop behavior."""

    def test_stop_when_not_running(self) -> None:
        """Stop is safe when not running."""
        mgr = SnapclientManager()
        mgr.stop()  # Should not raise
        assert mgr.status == "stopped"

    def test_stop_disables_auto_restart(self) -> None:
        """Stop disables auto-restart."""
        mgr = SnapclientManager()
        mgr.enable_auto_restart(True)
        mgr.stop()
        assert mgr._auto_restart is False  # pyright: ignore[reportPrivateUsage]


class TestSnapclientManagerRestart:
    """Test restart behavior."""

    def test_restart_raises_when_no_host(self) -> None:
        """Restart raises RuntimeError if start() was never called."""
        mgr = SnapclientManager()
        with pytest.raises(RuntimeError, match="no host configured"):
            mgr.restart()

    def test_restart_works_after_start(self) -> None:
        """Restart works when host was previously configured."""
        mgr = SnapclientManager()
        fake_binary = Path("/usr/bin/snapclient")

        with (
            patch("snapctrl.core.snapclient_manager.find_snapclient", return_value=fake_binary),
            patch.object(QProcess, "start"),
            patch.object(QProcess, "state", return_value=QProcess.ProcessState.NotRunning),
        ):
            mgr.start("192.168.1.100")
            mgr.restart()  # Should not raise


class TestSnapclientManagerConstants:
    """Test module-level constants."""

    def test_initial_backoff(self) -> None:
        """Initial backoff is 1 second."""
        assert INITIAL_BACKOFF_MS == 1000

    def test_max_backoff(self) -> None:
        """Max backoff is 30 seconds."""
        assert MAX_BACKOFF_MS == 30_000

    def test_backoff_multiplier(self) -> None:
        """Backoff doubles each time."""
        assert BACKOFF_MULTIPLIER == 2

    def test_terminate_timeout(self) -> None:
        """Terminate timeout is 3 seconds."""
        assert TERMINATE_TIMEOUT_MS == 3000

    def test_kill_timeout(self) -> None:
        """Kill timeout is 1 second."""
        assert KILL_TIMEOUT_MS == 1000

    def test_backoff_sequence(self) -> None:
        """Verify backoff sequence: 1s, 2s, 4s, 8s, 16s, 30s, 30s..."""
        backoff = INITIAL_BACKOFF_MS
        expected = [1000, 2000, 4000, 8000, 16000, 30000, 30000]
        for exp in expected:
            assert backoff == exp, f"Expected {exp}, got {backoff}"
            backoff = min(backoff * BACKOFF_MULTIPLIER, MAX_BACKOFF_MS)


class TestSnapclientManagerSignals:
    """Test signal emission."""

    def test_status_changed_emitted(self) -> None:
        """Status changes emit status_changed signal."""
        mgr = SnapclientManager()
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        mgr._set_status("starting")  # pyright: ignore[reportPrivateUsage]
        mgr._set_status("running")  # pyright: ignore[reportPrivateUsage]
        mgr._set_status("stopped")  # pyright: ignore[reportPrivateUsage]

        assert statuses == ["starting", "running", "stopped"]

    def test_no_duplicate_status_emission(self) -> None:
        """Same status doesn't re-emit signal."""
        mgr = SnapclientManager()
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        mgr._set_status("running")  # pyright: ignore[reportPrivateUsage]
        mgr._set_status("running")  # pyright: ignore[reportPrivateUsage]

        assert statuses == ["running"]


class TestSnapclientManagerDetach:
    """Test detach behavior."""

    def test_detach_when_not_running(self) -> None:
        """Detach does nothing when no process."""
        mgr = SnapclientManager()
        mgr.detach()  # Should not raise
        assert mgr.status == "stopped"

    def test_detach_clears_process(self) -> None:
        """Detach clears process reference without terminating."""
        mgr = SnapclientManager()
        fake_binary = Path("/usr/bin/snapclient")

        with (
            patch("snapctrl.core.snapclient_manager.find_snapclient", return_value=fake_binary),
            patch(
                "snapctrl.core.snapclient_manager.validate_snapclient",
                return_value=(True, "0.28.0"),
            ),
            patch.object(QProcess, "start"),
            patch.object(QProcess, "state", return_value=QProcess.ProcessState.Running),
        ):
            mgr.start("192.168.1.100")
            assert mgr._process is not None  # pyright: ignore[reportPrivateUsage]

            mgr.detach()

            assert mgr._process is None  # pyright: ignore[reportPrivateUsage]
            assert mgr.status == "stopped"
            assert not mgr._auto_restart  # pyright: ignore[reportPrivateUsage]

    def test_detach_emits_stopped_status(self) -> None:
        """Detach emits status_changed with 'stopped'."""
        mgr = SnapclientManager()
        fake_binary = Path("/usr/bin/snapclient")
        statuses: list[str] = []
        mgr.status_changed.connect(statuses.append)

        with (
            patch("snapctrl.core.snapclient_manager.find_snapclient", return_value=fake_binary),
            patch(
                "snapctrl.core.snapclient_manager.validate_snapclient",
                return_value=(True, "0.28.0"),
            ),
            patch.object(QProcess, "start"),
            patch.object(QProcess, "state", return_value=QProcess.ProcessState.Running),
        ):
            mgr.start("192.168.1.100")
            statuses.clear()  # Clear "starting" status

            mgr.detach()

            assert "stopped" in statuses
