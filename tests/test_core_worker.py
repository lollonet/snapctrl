"""Tests for SnapcastWorker (QThread worker for async client)."""

import pytest

from snapctrl.core.worker import SnapcastWorker


class TestSnapcastWorkerBasics:
    """Test basic SnapcastWorker functionality."""

    def test_initialization(self) -> None:
        """Test worker initialization."""
        worker = SnapcastWorker("192.168.1.100", 1705)

        assert worker.host == "192.168.1.100"
        assert worker.port == 1705
        assert not worker.is_connected
        assert worker._should_run is True

    def test_default_port(self) -> None:
        """Test default port is 1705."""
        worker = SnapcastWorker("192.168.1.100")
        assert worker.port == 1705


class TestSnapcastWorkerMethods:
    """Test worker methods."""

    def test_stop_sets_flag(self) -> None:
        """Test that stop sets the should_run flag."""
        worker = SnapcastWorker("192.168.1.100")
        assert worker._should_run is True

        worker.stop()
        assert worker._should_run is False


class TestSnapcastWorkerMocked:
    """Test worker with mocked client."""

    @pytest.mark.asyncio
    async def test_request_status_with_no_loop(self) -> None:
        """Test request_status is safe when loop not running."""
        worker = SnapcastWorker("192.168.1.100")
        # Should not crash
        worker.request_status()

    @pytest.mark.asyncio
    async def test_set_client_volume_with_no_loop(self) -> None:
        """Test set_client_volume is safe when loop not running."""
        worker = SnapcastWorker("192.168.1.100")
        # Should not crash
        worker.set_client_volume("client1", 50, False)

    @pytest.mark.asyncio
    async def test_set_group_mute_with_no_loop(self) -> None:
        """Test set_group_mute is safe when loop not running."""
        worker = SnapcastWorker("192.168.1.100")
        # Should not crash
        worker.set_group_mute("group1", True)

    @pytest.mark.asyncio
    async def test_set_group_stream_with_no_loop(self) -> None:
        """Test set_group_stream is safe when loop not running."""
        worker = SnapcastWorker("192.168.1.100")
        # Should not crash
        worker.set_group_stream("group1", "stream1")

    @pytest.mark.asyncio
    async def test_set_client_mute_with_no_loop(self) -> None:
        """Test set_client_mute is safe when loop not running."""
        worker = SnapcastWorker("192.168.1.100")
        # Should not crash
        worker.set_client_mute("client1", True)

    @pytest.mark.asyncio
    async def test_set_client_mute_unmute_with_no_loop(self) -> None:
        """Test set_client_mute unmute is safe when loop not running."""
        worker = SnapcastWorker("192.168.1.100")
        # Should not crash
        worker.set_client_mute("client1", False)


class TestSnapcastWorkerSignals:
    """Test that worker has required signals."""

    def test_has_connected_signal(self) -> None:
        """Test worker has connected signal."""
        worker = SnapcastWorker("192.168.1.100")
        assert hasattr(worker, "connected")

    def test_has_disconnected_signal(self) -> None:
        """Test worker has disconnected signal."""
        worker = SnapcastWorker("192.168.1.100")
        assert hasattr(worker, "disconnected")

    def test_has_connection_lost_signal(self) -> None:
        """Test worker has connection_lost signal."""
        worker = SnapcastWorker("192.168.1.100")
        assert hasattr(worker, "connection_lost")

    def test_has_state_received_signal(self) -> None:
        """Test worker has state_received signal."""
        worker = SnapcastWorker("192.168.1.100")
        assert hasattr(worker, "state_received")

    def test_has_error_occurred_signal(self) -> None:
        """Test worker has error_occurred signal."""
        worker = SnapcastWorker("192.168.1.100")
        assert hasattr(worker, "error_occurred")

    def test_has_notification_received_signal(self) -> None:
        """Test worker has notification_received signal."""
        worker = SnapcastWorker("192.168.1.100")
        assert hasattr(worker, "notification_received")


class TestSnapcastWorkerAutoReconnect:
    """Test auto-reconnect behavior."""

    def test_auto_reconnect_enabled_by_default(self) -> None:
        """Test that auto-reconnect is enabled by default."""
        worker = SnapcastWorker("192.168.1.100")
        assert worker._auto_reconnect is True

    def test_reconnect_delay_default(self) -> None:
        """Test default reconnect delay."""
        worker = SnapcastWorker("192.168.1.100")
        assert worker._reconnect_delay == 2.0
