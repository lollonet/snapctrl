"""Tests for network ping utilities."""

from snapcast_mvp.core.ping import (
    PingMonitor,
    RttThresholds,
    _parse_ping_output,
    format_rtt,
    get_rtt_color,
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
