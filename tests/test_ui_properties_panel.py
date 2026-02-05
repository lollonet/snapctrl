"""Tests for PropertiesPanel."""

from __future__ import annotations

import pytest
from pytestqt.qtbot import QtBot

from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.source import Source, SourceStatus
from snapctrl.ui.panels.properties import PropertiesPanel, _format_jitter


@pytest.fixture
def sample_group() -> Group:
    """Create a sample group."""
    return Group(
        id="g1",
        name="Living Room",
        stream_id="s1",
        muted=False,
        client_ids=["c1", "c2"],
    )


@pytest.fixture
def sample_client() -> Client:
    """Create a sample client."""
    return Client(
        id="c1-long-id-12345678",
        host="192.168.1.100",
        name="Test Client",
        volume=75,
        muted=False,
        connected=True,
        latency=50,
        snapclient_version="0.28.0",
        host_os="Linux",
        host_arch="aarch64",
        mac="aa:bb:cc:dd:ee:ff",
    )


@pytest.fixture
def sample_source() -> Source:
    """Create a sample source."""
    return Source(
        id="s1",
        name="MPD",
        status=SourceStatus.PLAYING,
        stream_type="pipe",
        codec="flac",
        sample_format="48000:16:2",
        uri_scheme="pipe",
    )


class TestPropertiesPanelCreation:
    """Test panel creation."""

    def test_creation(self, qtbot: QtBot) -> None:
        """Test panel can be created."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert panel is not None

    def test_initial_content(self, qtbot: QtBot) -> None:
        """Test initial placeholder content."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert "Select an item" in panel._content.text()

    def test_has_latency_signal(self, qtbot: QtBot) -> None:
        """Test panel has latency_changed signal."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)
        assert hasattr(panel, "latency_changed")


class TestPropertiesPanelClear:
    """Test clearing panel."""

    def test_clear(self, qtbot: QtBot, sample_group: Group) -> None:
        """Test clear restores placeholder."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_group(sample_group)
        panel.clear()

        assert "Select an item" in panel._content.text()


class TestPropertiesPanelSetGroup:
    """Test group display."""

    def test_set_group(self, qtbot: QtBot, sample_group: Group) -> None:
        """Test setting group updates content."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_group(sample_group)

        assert "Living Room" in panel._content.text()
        assert "g1" in panel._content.text()
        assert "s1" in panel._content.text()

    def test_set_group_muted(self, qtbot: QtBot) -> None:
        """Test setting muted group."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        group = Group(id="g1", name="Test", stream_id="s1", muted=True, client_ids=[])
        panel.set_group(group)

        assert "Muted" in panel._content.text()


class TestPropertiesPanelSetClient:
    """Test client display."""

    def test_set_client(self, qtbot: QtBot, sample_client: Client) -> None:
        """Test setting client updates content."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_client(sample_client)

        assert "Test Client" in panel._content.text()
        assert "192.168.1.100" in panel._content.text()
        assert "75%" in panel._content.text()
        assert "Connected" in panel._content.text()

    def test_set_client_disconnected(self, qtbot: QtBot) -> None:
        """Test setting disconnected client."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        client = Client(id="c1", host="192.168.1.100", connected=False, latency=50)
        panel.set_client(client)

        assert "Disconnected" in panel._content.text()
        # Disconnected clients show latency as text
        assert "50ms" in panel._content.text()

    def test_set_client_with_network_rtt(self, qtbot: QtBot, sample_client: Client) -> None:
        """Test setting client with network RTT."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_client(sample_client, network_rtt=10.5)

        assert "10.5" in panel._content.text() or "10" in panel._content.text()

    def test_set_client_with_time_stats(self, qtbot: QtBot, sample_client: Client) -> None:
        """Test setting client with server time stats."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        stats = {
            "jitter_median_ms": 2.5,
            "jitter_p95_ms": 5.0,
            "samples": 100,
        }
        panel.set_client(sample_client, time_stats=stats)

        assert "Jitter" in panel._content.text()
        assert "100" in panel._content.text()  # samples

    def test_set_client_measuring_latency(self, qtbot: QtBot) -> None:
        """Test connected client with no latency shows measuring."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        client = Client(id="c1", host="192.168.1.100", connected=True)
        panel.set_client(client)  # No network_rtt, no time_stats

        assert "Measuring" in panel._content.text()

    def test_set_client_creates_latency_widget(self, qtbot: QtBot, sample_client: Client) -> None:
        """Test connected client creates latency spinbox."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_client(sample_client)

        assert panel._latency_widget is not None
        assert panel._latency_spinbox is not None
        assert panel._current_client_id == sample_client.id

    def test_set_client_latency_value(self, qtbot: QtBot) -> None:
        """Test latency spinbox has correct initial value."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        client = Client(id="c1", host="h", connected=True, latency=100)
        panel.set_client(client)

        assert panel._latency_spinbox is not None
        assert panel._latency_spinbox.value() == 100


class TestPropertiesPanelSetSource:
    """Test source display."""

    def test_set_source(self, qtbot: QtBot, sample_source: Source) -> None:
        """Test setting source updates content."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_source(sample_source)

        assert "MPD" in panel._content.text()
        assert "Playing" in panel._content.text()
        assert "flac" in panel._content.text()

    def test_set_source_idle(self, qtbot: QtBot) -> None:
        """Test setting idle source."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        source = Source(id="s1", name="Test", status=SourceStatus.IDLE)
        panel.set_source(source)

        assert "Idle" in panel._content.text()


class TestPropertiesPanelLocalSnapclient:
    """Test local snapclient display."""

    def test_set_local_snapclient_running(self, qtbot: QtBot) -> None:
        """Test local snapclient running status."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_local_snapclient(
            status="running",
            binary_path="/usr/bin/snapclient",
            version="0.28.0",
            server_host="192.168.1.1",
            server_port=1704,
        )

        assert "Running" in panel._content.text()
        assert "/usr/bin/snapclient" in panel._content.text()
        assert "0.28.0" in panel._content.text()
        assert "192.168.1.1:1704" in panel._content.text()

    def test_set_local_snapclient_stopped(self, qtbot: QtBot) -> None:
        """Test local snapclient stopped status."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_local_snapclient(status="stopped")

        assert "Stopped" in panel._content.text()

    def test_set_local_snapclient_error(self, qtbot: QtBot) -> None:
        """Test local snapclient error status."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_local_snapclient(status="error")

        assert "Error" in panel._content.text()


class TestPropertiesPanelLatencyWidget:
    """Test latency widget management."""

    def test_latency_widget_removed_on_clear(self, qtbot: QtBot, sample_client: Client) -> None:
        """Test latency widget is removed on clear."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_client(sample_client)
        assert panel._latency_widget is not None

        panel.clear()
        assert panel._latency_widget is None

    def test_latency_widget_removed_on_set_group(
        self, qtbot: QtBot, sample_client: Client, sample_group: Group
    ) -> None:
        """Test latency widget is removed when showing group."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.set_client(sample_client)
        assert panel._latency_widget is not None

        panel.set_group(sample_group)
        assert panel._latency_widget is None

    def test_latency_changed_signal(self, qtbot: QtBot, sample_client: Client) -> None:
        """Test latency changed signal emission."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        received: list[tuple[str, int]] = []
        panel.latency_changed.connect(lambda cid, lat: received.append((cid, lat)))

        panel.set_client(sample_client)
        assert panel._latency_spinbox is not None

        panel._latency_spinbox.setValue(200)
        panel._on_latency_editing_finished()

        assert received == [(sample_client.id, 200)]


class TestPropertiesPanelRefreshTheme:
    """Test theme refresh."""

    def test_refresh_theme(self, qtbot: QtBot) -> None:
        """Test refresh_theme doesn't crash."""
        panel = PropertiesPanel()
        qtbot.addWidget(panel)

        panel.refresh_theme()  # Should not crash


class TestFormatJitter:
    """Test _format_jitter helper function."""

    def test_format_zero(self) -> None:
        """Test formatting near-zero jitter."""
        assert _format_jitter(0.0005) == "0µs"

    def test_format_microseconds(self) -> None:
        """Test formatting sub-millisecond jitter."""
        result = _format_jitter(0.5)
        assert "µs" in result
        assert "500" in result

    def test_format_small_milliseconds(self) -> None:
        """Test formatting small millisecond jitter."""
        result = _format_jitter(2.5)
        assert "ms" in result
        assert "2.5" in result

    def test_format_large_milliseconds(self) -> None:
        """Test formatting large millisecond jitter."""
        result = _format_jitter(50)
        assert "ms" in result
        assert "50" in result
