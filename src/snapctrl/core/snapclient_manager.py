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
import subprocess
import threading
import time

from PySide6.QtCore import QObject, QProcess, QTimer, Signal

from snapctrl.core.snapclient_binary import find_snapclient, validate_snapclient

logger = logging.getLogger(__name__)

# Auto-restart backoff constants
INITIAL_BACKOFF_MS = 1000
MAX_BACKOFF_MS = 30_000
BACKOFF_MULTIPLIER = 2
MAX_RESTART_ATTEMPTS = 5

# Graceful termination timeouts
TERMINATE_TIMEOUT_MS = 3000
KILL_TIMEOUT_MS = 1000
MAX_PORT = 65535

# Client ID max length and validation
MAX_CLIENT_ID_LEN = 64
_MAC_RE = re.compile(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")
_HOSTNAME_LABEL = r"[a-zA-Z0-9](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9])?"
_HOST_RE = re.compile(rf"^{_HOSTNAME_LABEL}(?:\.{_HOSTNAME_LABEL})*$")
_CLIENT_ID_RE = re.compile(r"\bhostID:\s*([a-zA-Z0-9:._-]+)")  # Pre-compiled for stdout parsing

# Dangerous snapclient flags that must not be set via extra_args
_BLOCKED_ARGS = frozenset({"--host", "--port", "--hostID", "--logsink", "--logfilter"})

# Process detection cache (reduces subprocess overhead from ~100ms to ~0ms for repeated calls)
_PROCESS_CHECK_CACHE_TTL = 2.0  # seconds
_process_check_cache: dict[str, tuple[float, bool]] = {}
_cache_lock = threading.Lock()  # Thread-safe cache access


def _do_process_check() -> bool:
    """Actually perform the process check (no caching)."""
    try:
        # Use pgrep for cross-platform process detection
        result = subprocess.run(
            ["pgrep", "-x", "snapclient"],
            capture_output=True,
            timeout=1,  # Short timeout to avoid UI freeze
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        # pgrep not available or timed out - try ps fallback
        try:
            result = subprocess.run(
                ["ps", "-A", "-o", "comm="],
                capture_output=True,
                text=True,
                timeout=1,  # Short timeout to avoid UI freeze
                check=False,
            )
            if result.returncode == 0:
                processes = result.stdout.strip().split("\n")
                return any(proc.strip() == "snapclient" for proc in processes)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return False


def is_snapclient_running() -> bool:
    """Check if a snapclient process is running on the system.

    Results are cached for 2 seconds to avoid expensive subprocess calls
    on repeated checks (e.g., during UI updates).

    Thread-safe: Uses lock for cache access.

    Returns:
        True if snapclient is found in the process list.
    """
    cache_key = "snapclient"
    now = time.monotonic()

    with _cache_lock:
        # Check cache
        if cache_key in _process_check_cache:
            cached_time, cached_result = _process_check_cache[cache_key]
            if now - cached_time < _PROCESS_CHECK_CACHE_TTL:
                return cached_result

    # Cache miss - perform actual check (outside lock to avoid blocking)
    result = _do_process_check()

    with _cache_lock:
        _process_check_cache[cache_key] = (now, result)
    return result


def invalidate_process_cache() -> None:
    """Invalidate the process check cache.

    Call this after starting/stopping a process to force a fresh check.
    Thread-safe: Uses lock for cache access.
    """
    with _cache_lock:
        _process_check_cache.clear()


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

    status_changed = Signal(str)  # "running", "stopped", "starting", "error", "external"
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
        self._consecutive_failures = 0
        self._is_external = False  # True if using externally-started snapclient
        self._restart_timer = QTimer(self)
        self._restart_timer.setSingleShot(True)
        self._restart_timer.timeout.connect(self._do_restart)

    @property
    def status(self) -> str:
        """Return current status string."""
        return self._status

    @property
    def is_running(self) -> bool:
        """Return True if the snapclient process is running (managed or external)."""
        if self._is_external:
            return True
        return (
            self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning
        )

    @property
    def is_external(self) -> bool:
        """Return True if using an externally-started snapclient."""
        return self._is_external

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

        If already running (either managed by this instance or externally),
        stops or reports the existing process first.

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

        # Refresh external status in case it was killed since we last checked
        self.refresh_external_status()

        # Check if snapclient is already running on the system (not managed by us)
        if not self._process and is_snapclient_running():
            logger.info("Detected external snapclient already running, adopting it")
            self._is_external = True
            self._host = host
            self._port = port
            self._set_status("external")
            return

        if self.is_running:
            logger.info("Stopping existing snapclient before restart")
            self._auto_restart = False  # Prevent auto-restart during teardown
            self._restart_timer.stop()
            try:
                self.stop()
            except Exception:
                logger.exception("Failed to stop existing process cleanly")
                self._cleanup_process()
                self._set_status("stopped")

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

        is_valid, version_or_error = validate_snapclient(binary)
        if not is_valid:
            msg = f"Invalid snapclient binary: {version_or_error}"
            logger.error(msg)
            self._set_status("error")
            self.error_occurred.emit(msg)
            return

        logger.info("Using snapclient %s at %s", version_or_error, binary)
        self._binary_path = str(binary)
        self._launch()

    def stop(self) -> None:
        """Stop the snapclient subprocess gracefully."""
        self._auto_restart = False
        self._restart_timer.stop()

        # If using external snapclient, we don't manage its lifecycle
        if self._is_external:
            logger.info("External snapclient - not stopping (not managed by us)")
            self._is_external = False
            self._set_status("stopped")
            return

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
        invalidate_process_cache()  # Force fresh check after stopping

    def restart(self) -> None:
        """Restart the snapclient subprocess.

        Raises:
            RuntimeError: If no host has been configured (start() never called).
        """
        if not self._host:
            msg = "Cannot restart: no host configured (call start() first)"
            raise RuntimeError(msg)

        # Capture state before stop() modifies it
        restart_host = self._host
        restart_port = self._port
        was_auto_restart = self._auto_restart
        if self.is_running:
            self.stop()
        self._auto_restart = was_auto_restart
        self.start(restart_host, restart_port)

    def enable_auto_restart(self, enabled: bool = True) -> None:
        """Enable or disable auto-restart on crash.

        Args:
            enabled: Whether to auto-restart.
        """
        self._auto_restart = enabled

    def detect_external(self) -> bool:
        """Check if an external snapclient is running and adopt it.

        Returns:
            True if external snapclient was detected and adopted.
        """
        if self._process is not None:
            return False  # Already managing our own process

        invalidate_process_cache()  # Force fresh check
        if is_snapclient_running():
            logger.info("Detected external snapclient running")
            self._is_external = True
            self._set_status("external")
            return True
        return False

    def refresh_external_status(self) -> None:
        """Check if external snapclient is still running.

        If we were using an external snapclient and it stopped,
        update status to stopped.
        """
        if not self._is_external:
            return

        if not is_snapclient_running():
            logger.info("External snapclient stopped")
            self._is_external = False
            invalidate_process_cache()  # Ensure cache reflects new state
            self._set_status("stopped")

    def _launch(self) -> None:
        """Launch the snapclient process."""
        if self._binary_path is None:
            return

        # Clean up any existing process first (prevents memory leak)
        if self._process is not None:
            self._cleanup_process()

        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._on_stdout)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)

        args = self._build_args()
        logger.info("Starting snapclient: %r %r", self._binary_path, args)

        self._set_status("starting")
        self._process.start(self._binary_path, args)
        invalidate_process_cache()  # Force fresh check after starting

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
                self._consecutive_failures = 0
                continue  # Skip regex check - connection line won't have hostID

            # Detect client ID from output (e.g. "hostID: aa:bb:cc:dd:ee:ff")
            id_match = _CLIENT_ID_RE.search(line)
            if id_match:
                client_id = id_match.group(1)
                # Validate client ID: MAC address or hostname format
                if len(client_id) <= MAX_CLIENT_ID_LEN and (
                    _MAC_RE.match(client_id) or _HOST_RE.match(client_id)
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
        if not self._binary_path or not self._auto_restart:
            return

        if self._consecutive_failures >= MAX_RESTART_ATTEMPTS:
            logger.error(
                "Auto-restart disabled after %d consecutive failures",
                self._consecutive_failures,
            )
            self._auto_restart = False
            self._set_status("error")
            self.error_occurred.emit("Auto-restart disabled due to repeated failures")
            return

        self._consecutive_failures += 1
        logger.info(
            "Auto-restarting snapclient (attempt %d/%d)",
            self._consecutive_failures,
            MAX_RESTART_ATTEMPTS,
        )
        self._launch()

    def _set_status(self, status: str) -> None:
        """Update status and emit signal if changed.

        Args:
            status: New status string.
        """
        if status != self._status:
            self._status = status
            self.status_changed.emit(status)

    def detach(self) -> None:
        """Detach the running process so it survives app exit.

        After calling this, the process continues running independently
        and this manager no longer tracks it.
        """
        if self._process is None:
            return

        self._auto_restart = False
        self._restart_timer.stop()

        # Disconnect signals so we don't receive events
        try:
            self._process.readyReadStandardOutput.disconnect(self._on_stdout)
            self._process.finished.disconnect(self._on_finished)
            self._process.errorOccurred.disconnect(self._on_error)
        except RuntimeError:
            pass  # Already disconnected

        # Clear our reference without calling deleteLater() or terminate()
        # The QProcess will be orphaned but the child process continues
        self._process.setParent(None)  # Prevent destruction with parent
        self._process = None
        self._set_status("stopped")
        logger.info("Detached snapclient process (will continue running)")

    def _cleanup_process(self) -> None:
        """Clean up the QProcess instance."""
        if self._process is not None:
            try:
                self._process.readyReadStandardOutput.disconnect(self._on_stdout)
                self._process.finished.disconnect(self._on_finished)
                self._process.errorOccurred.disconnect(self._on_error)
            except RuntimeError:
                logger.debug("Signals already disconnected during cleanup")
            self._process.deleteLater()
            self._process = None
