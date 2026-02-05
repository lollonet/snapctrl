"""Tests for network ping utilities."""

import subprocess
from unittest.mock import MagicMock, patch

from snapctrl.core.ping import (
    PingMonitor,
    RttThresholds,
    _parse_ping_output,
    format_rtt,
    get_rtt_color,
    ping_host_sync,
)


class TestParsePingOutput:
    """Tests for _parse_ping_output function."""

    def test_parse_macos_linux_format(self) -> None:
        """Test parsing macOS/Linux ping output."""
        output = "64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=5.432 ms"
        assert _parse_ping_output(output) == 5.432

    def test_parse_windows_format(self) -> None:
        """Test parsing Windows ping output."""
        output = "Reply from 192.168.1.1: bytes=32 time=5ms TTL=64"
        assert _parse_ping_output(output) == 5.0

    def test_parse_windows_less_than_1ms(self) -> None:
        """Test parsing Windows ping with time<1ms."""
        output = "Reply from 192.168.1.1: bytes=32 time<1ms TTL=64"
        assert _parse_ping_output(output) == 1.0

    def test_parse_german_windows(self) -> None:
        """Test parsing German Windows ping output."""
        output = "Antwort von 192.168.1.1: Bytes=32 Zeit=5ms TTL=64"
        assert _parse_ping_output(output) == 5.0

    def test_parse_italian_format(self) -> None:
        """Test parsing Italian ping output."""
        output = "64 bytes da 192.168.1.1: tempo=5.0 ms"
        assert _parse_ping_output(output) == 5.0

    def test_parse_no_match(self) -> None:
        """Test parsing output with no match."""
        output = "Request timed out."
        assert _parse_ping_output(output) is None

    def test_parse_empty_output(self) -> None:
        """Test parsing empty output."""
        assert _parse_ping_output("") is None


class TestFormatRtt:
    """Tests for format_rtt function."""

    def test_format_none(self) -> None:
        """Test formatting None value."""
        assert format_rtt(None) == "N/A"

    def test_format_sub_millisecond(self) -> None:
        """Test formatting sub-millisecond RTT."""
        assert format_rtt(0.5) == "<1ms"
        assert format_rtt(0.1) == "<1ms"

    def test_format_below_precision_threshold(self) -> None:
        """Test formatting RTT below precision threshold."""
        assert format_rtt(5.123) == "5.1ms"
        assert format_rtt(1.0) == "1.0ms"
        assert format_rtt(9.999) == "10.0ms"

    def test_format_above_precision_threshold(self) -> None:
        """Test formatting RTT above precision threshold."""
        assert format_rtt(15.7) == "15ms"
        assert format_rtt(100.5) == "100ms"

    def test_format_exactly_one(self) -> None:
        """Test formatting RTT of exactly 1ms."""
        assert format_rtt(1.0) == "1.0ms"


class TestGetRttColor:
    """Tests for get_rtt_color function."""

    def test_good_latency(self) -> None:
        """Test color for good latency."""
        assert get_rtt_color(10.0) == "#80ff80"
        assert get_rtt_color(49.9) == "#80ff80"

    def test_warning_latency(self) -> None:
        """Test color for warning latency."""
        assert get_rtt_color(50.0) == "#ffff80"
        assert get_rtt_color(75.0) == "#ffff80"
        assert get_rtt_color(99.9) == "#ffff80"

    def test_high_latency(self) -> None:
        """Test color for high latency."""
        assert get_rtt_color(100.0) == "#ff8080"
        assert get_rtt_color(500.0) == "#ff8080"

    def test_threshold_constants(self) -> None:
        """Verify threshold constants are as expected."""
        assert RttThresholds.GOOD == 50
        assert RttThresholds.WARN == 100
        assert RttThresholds.PRECISION == 10


class TestPingMonitor:
    """Tests for PingMonitor class."""

    def test_init_defaults(self) -> None:
        """Test PingMonitor initialization with defaults."""
        monitor = PingMonitor()
        assert monitor._interval_sec == 15.0
        assert monitor._hosts == {}
        assert monitor._results == {}
        assert not monitor._running

    def test_init_custom_interval(self) -> None:
        """Test PingMonitor initialization with custom interval."""
        monitor = PingMonitor(interval_sec=30.0)
        assert monitor._interval_sec == 30.0

    def test_set_hosts(self) -> None:
        """Test setting hosts to ping."""
        monitor = PingMonitor()
        hosts = {"client1": "192.168.1.10", "client2": "192.168.1.11"}
        monitor.set_hosts(hosts)
        assert monitor._hosts == hosts

    def test_set_hosts_copies_dict(self) -> None:
        """Test that set_hosts makes a copy of the dict."""
        monitor = PingMonitor()
        hosts = {"client1": "192.168.1.10"}
        monitor.set_hosts(hosts)
        hosts["client2"] = "192.168.1.11"
        assert "client2" not in monitor._hosts

    def test_set_interval(self) -> None:
        """Test setting the ping interval."""
        monitor = PingMonitor()
        monitor.set_interval(5.0)
        assert monitor._interval_sec == 5.0

    def test_get_result_no_results(self) -> None:
        """Test getting result when no results exist."""
        monitor = PingMonitor()
        assert monitor.get_result("client1") is None

    def test_results_property_returns_copy(self) -> None:
        """Test that results property returns a copy."""
        monitor = PingMonitor()
        monitor._results = {"client1": 5.0}
        results = monitor.results
        results["client2"] = 10.0
        assert "client2" not in monitor._results

    def test_start_stop(self) -> None:
        """Test starting and stopping the monitor."""
        monitor = PingMonitor(interval_sec=60.0)  # Long interval to avoid pings
        monitor.set_hosts({})  # No hosts to ping

        assert not monitor._running
        monitor.start()
        assert monitor._running
        assert monitor._thread is not None

        monitor.stop()
        assert not monitor._running
        assert monitor._thread is None

    def test_start_idempotent(self) -> None:
        """Test that calling start twice doesn't create multiple threads."""
        monitor = PingMonitor(interval_sec=60.0)
        monitor.set_hosts({})

        monitor.start()
        thread1 = monitor._thread
        monitor.start()  # Second call should be no-op
        assert monitor._thread is thread1

        monitor.stop()


class TestPingHostSync:
    """Tests for ping_host_sync function."""

    def test_ping_success_macos(self) -> None:
        """Test successful ping on macOS."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "64 bytes from 192.168.1.1: icmp_seq=0 ttl=64 time=5.432 ms"

        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            rtt = ping_host_sync("192.168.1.1", timeout=2.0)

            assert rtt == 5.432
            # Verify macOS command format
            mock_run.assert_called_once()
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "ping"
            assert "-c" in cmd
            assert "-W" in cmd

    def test_ping_success_linux(self) -> None:
        """Test successful ping on Linux."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "64 bytes from 192.168.1.1: icmp_seq=1 ttl=64 time=3.21 ms"

        with (
            patch("platform.system", return_value="Linux"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            rtt = ping_host_sync("192.168.1.1", timeout=2.0)

            assert rtt == 3.21
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "ping"
            assert "-c" in cmd

    def test_ping_success_windows(self) -> None:
        """Test successful ping on Windows."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Reply from 192.168.1.1: bytes=32 time=5ms TTL=64"

        with (
            patch("platform.system", return_value="Windows"),
            patch("subprocess.run", return_value=mock_result) as mock_run,
        ):
            rtt = ping_host_sync("192.168.1.1", timeout=2.0)

            assert rtt == 5.0
            cmd = mock_run.call_args[0][0]
            assert cmd[0] == "ping"
            assert "-n" in cmd
            assert "-w" in cmd

    def test_ping_failure_nonzero_return(self) -> None:
        """Test ping failure with non-zero return code."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = "Request timed out."

        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run", return_value=mock_result),
        ):
            rtt = ping_host_sync("192.168.1.1")

            assert rtt is None

    def test_ping_timeout_expired(self) -> None:
        """Test ping timeout expired."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run", side_effect=subprocess.TimeoutExpired("ping", 3.0)),
        ):
            rtt = ping_host_sync("192.168.1.1", timeout=2.0)

            assert rtt is None

    def test_ping_os_error(self) -> None:
        """Test ping with OSError (e.g., ping command not found)."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run", side_effect=OSError("No such file")),
        ):
            rtt = ping_host_sync("192.168.1.1")

            assert rtt is None

    def test_ping_subprocess_error(self) -> None:
        """Test ping with generic subprocess error."""
        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run", side_effect=subprocess.SubprocessError("Unknown error")),
        ):
            rtt = ping_host_sync("192.168.1.1")

            assert rtt is None

    def test_ping_parse_failure(self) -> None:
        """Test ping when output cannot be parsed."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Unknown output format"

        with (
            patch("platform.system", return_value="Darwin"),
            patch("subprocess.run", return_value=mock_result),
        ):
            rtt = ping_host_sync("192.168.1.1")

            assert rtt is None


class TestPingMonitorInternal:
    """Test PingMonitor internal methods."""

    def test_ping_all_empty_hosts(self) -> None:
        """Test _ping_all with no hosts."""
        monitor = PingMonitor()
        monitor._hosts = {}

        # Should not crash
        monitor._ping_all()

        assert monitor._results == {}

    def test_ping_all_with_hosts(self) -> None:
        """Test _ping_all with hosts."""
        monitor = PingMonitor()
        monitor._hosts = {"c1": "192.168.1.10"}
        monitor._running = True

        results_received: list[dict] = []
        monitor.results_updated.connect(results_received.append)

        with patch("snapctrl.core.ping.ping_host_sync", return_value=5.5):
            monitor._ping_all()

        assert len(results_received) == 1
        assert results_received[0] == {"c1": 5.5}

    def test_ping_all_stops_when_not_running(self) -> None:
        """Test _ping_all stops early when monitor stops."""
        monitor = PingMonitor()
        monitor._hosts = {"c1": "192.168.1.10", "c2": "192.168.1.11"}
        monitor._running = False  # Already stopped

        call_count = 0

        def mock_ping(host: str, timeout: float = 2.0) -> float | None:
            nonlocal call_count
            call_count += 1
            return 1.0

        with patch("snapctrl.core.ping.ping_host_sync", side_effect=mock_ping):
            monitor._ping_all()

        # Should not ping any hosts because _running is False
        assert call_count == 0
