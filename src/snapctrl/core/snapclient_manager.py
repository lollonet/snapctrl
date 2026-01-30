"""Snapclient subprocess manager using QProcess.

Manages the lifecycle of a local snapclient process: start, stop,
auto-restart on crash with exponential backoff, and status reporting.

All audio control (volume, mute, groups) goes through the snapserver
JSON-RPC API — this module only manages the subprocess lifecycle.

Usage:
    from snapctrl.core.snapclient_manager import SnapclientManager

    mgr = SnapclientManager()
    mgr.status_changed.connect(on_status)
    mgr.start("192.168.1.100")
"""

from __future__ import annotations

import logging
import re

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from snapctrl.core.snapclient_binary import find_snapclient

logger = logging.getLogger(__name__)

# Auto-restart backoff constants
INITIAL_BACKOFF_MS = 1000
MAX_BACKOFF_MS = 30_000
BACKOFF_MULTIPLIER = 2

# Graceful termination timeouts
TERMINATE_TIMEOUT_MS = 3000
KILL_TIMEOUT_MS = 1000
MAX_PORT = 65535

# Client ID max length and validation
MAX_CLIENT_ID_LEN = 64
_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_HOST_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")

# Dangerous snapclient flags that must not be set via extra_args
_BLOCKED_ARGS = frozenset({"--host", "--port", "--hostID", "--logsink", "--logfilter"})


class SnapclientManager(QObject):
    """Manages a local snapclient subprocess.

    Uses QProcess for Qt event loop integration — no additional
    threads needed.  Emits signals for status changes and errors.

    Signals:
        status_changed: Emitted when status changes (status string).
        error_occurred: Emitted on errors (error message).
        client_id_detected: Emitted when client ID is parsed from output.

    Example:
        mgr = SnapclientManager()
        mgr.status_changed.connect(lambda s: print(f"Status: {s}"))
        mgr.start("192.168.1.100")
    """

    status_changed = Signal(str)  # "running", "stopped", "starting", "error"
    error_occurred = Signal(str)  # error message
    client_id_detected = Signal(str)  # client ID from snapclient output

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._process: QProcess | None = None
        self._status = "stopped"
        self._host = ""
        self._port = 1704
        self._host_id = ""
        self._extra_args: list[str] = []
        self._binary_path: str | None = None
        self._configured_binary_path: str | None = None
        self._auto_restart = True
        self._backoff_ms = INITIAL_BACKOFF_MS
        self._restart_timer = QTimer(self)
        self._restart_timer.setSingleShot(True)
        self._restart_timer.timeout.connect(self._do_restart)

    @property
    def status(self) -> str:
        """Return current status string."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Return True if the snapclient process is running."""
        return (
            self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning
        )

    def set_configured_binary_path(self, path: str | None) -> None:
        """Set user-configured binary path for discovery.

        Args:
            path: Path to snapclient binary, or None to use auto-discovery.
        """
        self._configured_binary_path = path

    def set_extra_args(self, args: list[str]) -> None:
        """Set additional CLI arguments for snapclient.

        Args:
            args: List of extra arguments.

        Raises:
            ValueError: If args contain blocked flags managed internally.
        """
        blocked = [a for a in args if a in _BLOCKED_ARGS or a.split("=", 1)[0] in _BLOCKED_ARGS]
        if blocked:
            msg = f"Blocked arguments (managed internally): {blocked}"
            raise ValueError(msg)
        self._extra_args = args.copy()

    def set_host_id(self, host_id: str) -> None:
        """Set custom host ID (default uses MAC address).

        Args:
            host_id: Custom host ID string.
        """
        self._host_id = host_id

    def start(self, host: str, port: int = 1704) -> None:
        """Start the snapclient subprocess.

        If already running, stops the current process first.

        Args:
            host: Snapserver hostname or IP.
            port: Snapserver port (default 1704).

        Raises:
            ValueError: If host is empty or port is out of range.
        """
        if not host.strip():
            msg = "Host must not be empty or whitespace-only"
            raise ValueError(msg)
        if not (1 <= port <= MAX_PORT):
            msg = f"Port must be 1–{MAX_PORT}, got {port}"
            raise ValueError(msg)

        if self.is_running:
            logger.info("Stopping existing snapclient before restart")
            self._auto_restart = False  # Prevent auto-restart during teardown
            self._restart_timer.stop()
            self.stop()

        self._auto_restart = True
        self._host = host
        self._port = port
        self._backoff_ms = INITIAL_BACKOFF_MS

        binary = find_snapclient(self._configured_binary_path)
        if binary is None:
            msg = "snapclient binary not found"
            logger.error(msg)
            self._set_status("error")
            self.error_occurred.emit(msg)
            return

        self._binary_path = str(binary)
        self._launch()

    def stop(self) -> None:
        """Stop the snapclient subprocess gracefully."""
        self._auto_restart = False
        self._restart_timer.stop()

        if self._process is not None:
            if self._process.state() != QProcess.ProcessState.NotRunning:
                logger.info("Stopping snapclient (SIGTERM)")
                # Note: waitForFinished() blocks the Qt event loop during
                # shutdown.  This is intentional — we need a clean process
                # teardown before the app exits or before a restart, and the
                # timeouts (3 s + 1 s) keep the blocking bounded.
                self._process.terminate()
                if (
                    self._process.state() != QProcess.ProcessState.NotRunning
                    and not self._process.waitForFinished(TERMINATE_TIMEOUT_MS)
                ):
                    logger.warning("snapclient did not stop, killing")
                    self._process.kill()
                    if not self._process.waitForFinished(KILL_TIMEOUT_MS):
                        logger.error("snapclient could not be killed")
            self._cleanup_process()

        self._set_status("stopped")

    def restart(self) -> None:
        """Restart the snapclient subprocess.

        Raises:
            RuntimeError: If no host has been configured (start() never called).
        """
        if not self._host:
            msg = "Cannot restart: no host configured (call start() first)"
            raise RuntimeError(msg)

        # Capture connection info before stop() clears _auto_restart
        restart_host = self._host
        restart_port = self._port
        if self.is_running:
            self.stop()
        self._auto_restart = True
        self.start(restart_host, restart_port)

    def enable_auto_restart(self, enabled: bool = True) -> None:
        """Enable or disable auto-restart on crash.

        Args:
            enabled: Whether to auto-restart.
        """
        self._auto_restart = enabled

    def _launch(self) -> None:
        """Launch the snapclient process."""
        if self._binary_path is None:
            return

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        args = self._build_args()
        logger.info("Starting snapclient: %r %r", self._binary_path, args)

        self._set_status("starting")
        self._process.start(self._binary_path, args)

    def _build_args(self) -> list[str]:
        """Build snapclient CLI arguments."""
        args = [
            "--host",
            self._host,
            "--port",
            str(self._port),
            "--logsink",
            "stdout",
            "--logfilter",
            "*:info",
        ]
        if self._host_id:
            args.extend(["--hostID", self._host_id])
        args.extend(self._extra_args)
        return args

    def _on_stdout(self) -> None:
        """Handle stdout data from snapclient."""
        if self._process is None:
            return

        data = self._process.readAllStandardOutput()
        raw = bytes(data.data())
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            logger.warning("snapclient output contained invalid UTF-8, using replacement")
            text = raw.decode("utf-8", errors="replace")

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            logger.debug("snapclient: %s", line)

            # Detect successful connection (snapclient v0.28–v0.31 output format)
            if "Connected to" in line:
                self._set_status("running")
                self._backoff_ms = INITIAL_BACKOFF_MS

            # Detect client ID from output (e.g. "hostID: aa:bb:cc:dd:ee:ff")
            if "hostID:" in line:
                parts = line.split("hostID:", 1)
                if len(parts) > 1:
                    client_id = parts[1].strip()
                    # Validate client ID: MAC address or hostname format
                    if (
                        client_id
                        and len(client_id) <= MAX_CLIENT_ID_LEN
                        and (_MAC_RE.match(client_id) or _HOST_RE.match(client_id))
                    ):
                        logger.info("Detected client ID: %s", client_id)
                        self.client_id_detected.emit(client_id)
                    else:
                        logger.warning("Invalid client ID format: %r", client_id)

    def _on_finished(self, exit_code: int, exit_status: QProcess.ExitStatus) -> None:
        """Handle process exit.

        Args:
            exit_code: Process exit code.
            exit_status: Qt exit status (Normal or Crash).
        """
        if exit_status == QProcess.ExitStatus.CrashExit:
            logger.warning("snapclient crashed (exit code %d)", exit_code)
            self._set_status("error")
            self.error_occurred.emit(f"snapclient crashed (exit code {exit_code})")
        else:
            logger.info("snapclient exited normally (exit code %d)", exit_code)

        self._cleanup_process()

        if self._auto_restart and exit_status == QProcess.ExitStatus.CrashExit:
            logger.info("Auto-restarting in %d ms", self._backoff_ms)
            self._restart_timer.start(self._backoff_ms)
            self._backoff_ms = min(self._backoff_ms * BACKOFF_MULTIPLIER, MAX_BACKOFF_MS)
        else:
            self._set_status("stopped")

    def _on_error(self, error: QProcess.ProcessError) -> None:
        """Handle QProcess errors.

        Args:
            error: The process error type.
        """
        error_map = {
            QProcess.ProcessError.FailedToStart: "Failed to start snapclient",
            QProcess.ProcessError.Crashed: "snapclient crashed",
            QProcess.ProcessError.Timedout: "snapclient timed out",
            QProcess.ProcessError.WriteError: "Write error",
            QProcess.ProcessError.ReadError: "Read error",
            QProcess.ProcessError.UnknownError: "Unknown error",
        }
        msg = error_map.get(error, f"Process error: {error}")
        logger.error("snapclient error: %s", msg)
        self._set_status("error")
        self.error_occurred.emit(msg)

    def _do_restart(self) -> None:
        """Execute auto-restart."""
        if self._binary_path and self._auto_restart:
            logger.info("Auto-restarting snapclient")
            self._launch()

    def _set_status(self, status: str) -> None:
        """Update status and emit signal if changed.

        Args:
            status: New status string.
        """
        if status != self._status:
            self._status = status
            self.status_changed.emit(status)

    def _cleanup_process(self) -> None:
        """Clean up the QProcess instance."""
        if self._process is not None:
            try:
                self._process.readyReadStandardOutput.disconnect(self._on_stdout)
                self._process.finished.disconnect(self._on_finished)
                self._process.errorOccurred.disconnect(self._on_error)
            except (RuntimeError, TypeError):
                logger.debug("Signal disconnect during cleanup (already disconnected)")
            self._process.deleteLater()
            self._process = None
