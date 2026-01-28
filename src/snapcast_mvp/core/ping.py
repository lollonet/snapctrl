"""Network ping monitor for measuring RTT to Snapcast clients.

Note: RTT measurement may not work for all clients. Some network configurations
(firewalls, ICMP blocking, VPNs) can prevent ping responses even when the client
is reachable for audio streaming.
"""

import logging
import platform
import re
import subprocess
import threading
import time

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


def _parse_ping_output(output: str) -> float | None:
    """Parse ping output to extract RTT in milliseconds.

    Args:
        output: Raw ping command output.

    Returns:
        RTT in milliseconds, or None if parsing failed.
    """
    # macOS/Linux: "time=X.XXX ms" or "time=X ms"
    # Windows: "time=Xms" or "time<1ms"
    patterns = [
        r"time[=<](\d+\.?\d*)\s*ms",  # Standard format
        r"Zeit[=<](\d+\.?\d*)\s*ms",  # German Windows
        r"tempo[=<](\d+\.?\d*)\s*ms",  # Italian
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE)
        if match:
            return float(match.group(1))

    return None


def ping_host_sync(host: str, timeout: float = 2.0) -> float | None:
    """Ping a host and return RTT in milliseconds (synchronous).

    Uses system ping command via subprocess (not shell) for safety.
    The host parameter should be an IP address from trusted source (Snapcast server).

    Args:
        host: IP address or hostname to ping.
        timeout: Timeout in seconds.

    Returns:
        RTT in milliseconds, or None if unreachable.
    """
    system = platform.system().lower()

    if system == "windows":
        # Windows: ping -n 1 -w <timeout_ms>
        cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
    elif system == "darwin":
        # macOS: ping -c 1 -W <timeout_ms> (macOS uses milliseconds!)
        cmd = ["ping", "-c", "1", "-W", str(int(timeout * 1000)), host]
    else:
        # Linux: ping -c 1 -W <timeout_s>
        cmd = ["ping", "-c", "1", "-W", str(int(timeout)), host]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=timeout + 1,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return _parse_ping_output(result.stdout)
        # Ping failed (host unreachable, network error, etc.)
        logger.debug("Ping to %s failed with return code %d", host, result.returncode)
    except subprocess.TimeoutExpired:
        logger.debug("Ping to %s timed out after %.1fs", host, timeout)
    except OSError as e:
        logger.warning("Ping command failed for %s: %s", host, e)
    except subprocess.SubprocessError as e:
        logger.debug("Ping subprocess error for %s: %s", host, e)

    return None


class PingMonitor(QObject):
    """Monitor network RTT to Snapcast clients.

    Periodically pings client IPs in a background thread and emits results via signal.

    Example:
        monitor = PingMonitor(interval_sec=15)
        monitor.results_updated.connect(lambda r: print(r))
        monitor.set_hosts({"client1": "192.168.1.10", "client2": "192.168.1.11"})
        monitor.start()
    """

    # Signal emitted when ping results are updated
    # Dict maps client_id -> rtt_ms (or None if unreachable)
    results_updated = Signal(dict)  # {client_id: float | None}

    def __init__(
        self,
        interval_sec: float = 15.0,
        parent: QObject | None = None,
    ) -> None:
        """Initialize the ping monitor.

        Args:
            interval_sec: Interval between ping rounds in seconds.
            parent: Optional parent QObject.
        """
        super().__init__(parent)
        self._interval_sec = interval_sec
        self._hosts: dict[str, str] = {}  # client_id -> ip
        self._results: dict[str, float | None] = {}  # client_id -> rtt_ms
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def set_hosts(self, hosts: dict[str, str]) -> None:
        """Set the hosts to ping.

        Args:
            hosts: Dict mapping client_id -> IP address.
        """
        with self._lock:
            self._hosts = hosts.copy()

    def set_interval(self, interval_sec: float) -> None:
        """Set the ping interval.

        Args:
            interval_sec: Interval in seconds.
        """
        self._interval_sec = interval_sec

    def start(self) -> None:
        """Start the ping monitor."""
        if not self._running:
            self._running = True
            self._thread = threading.Thread(target=self._ping_loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """Stop the ping monitor."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=3.0)
            self._thread = None

    def get_result(self, client_id: str) -> float | None:
        """Get the last ping result for a client.

        Args:
            client_id: The client ID.

        Returns:
            RTT in ms, or None if not available/unreachable.
        """
        return self._results.get(client_id)

    @property
    def results(self) -> dict[str, float | None]:
        """Return all current ping results."""
        return self._results.copy()

    def _ping_loop(self) -> None:
        """Background thread: periodically ping all hosts."""
        while self._running:
            self._ping_all()
            # Sleep in small increments to allow quick shutdown
            for _ in range(int(self._interval_sec * 10)):
                if not self._running:
                    break
                time.sleep(0.1)

    def _ping_all(self) -> None:
        """Ping all hosts and emit results."""
        with self._lock:
            hosts = self._hosts.copy()

        if not hosts:
            return

        results: dict[str, float | None] = {}
        for client_id, ip in hosts.items():
            if not self._running:
                break
            results[client_id] = ping_host_sync(ip)

        self._results = results
        # Emit signal (Qt handles thread safety for signals)
        self.results_updated.emit(results)


class RttThresholds:
    """RTT display thresholds for categorizing network latency.

    These values are chosen based on typical home network performance
    and audio streaming requirements:
    - <50ms: Excellent for real-time audio sync (green)
    - 50-100ms: Acceptable but may cause minor sync issues (yellow)
    - >100ms: High latency, likely to cause audible sync problems (red)
    """

    # Show decimal precision below 10ms (sub-10ms is excellent)
    PRECISION = 10
    # Green indicator below 50ms (good for real-time audio)
    GOOD = 50
    # Yellow 50-100ms, red above 100ms (audio may stutter)
    WARN = 100


def format_rtt(rtt_ms: float | None) -> str:
    """Format RTT for display.

    Args:
        rtt_ms: RTT in milliseconds, or None.

    Returns:
        Formatted string like "5.2ms" or "N/A".
    """
    if rtt_ms is None:
        return "N/A"
    if rtt_ms < 1:
        return "<1ms"
    if rtt_ms < RttThresholds.PRECISION:
        return f"{rtt_ms:.1f}ms"
    return f"{int(rtt_ms)}ms"


def get_rtt_color(rtt_ms: float) -> str:
    """Get the display color for an RTT value.

    Args:
        rtt_ms: RTT in milliseconds.

    Returns:
        HTML color code: green for good, yellow for warning, red for high latency.
    """
    if rtt_ms < RttThresholds.GOOD:
        return "#80ff80"  # Green - good
    if rtt_ms < RttThresholds.WARN:
        return "#ffff80"  # Yellow - warning
    return "#ff8080"  # Red - high latency
