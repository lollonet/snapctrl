"""Extended tests for SnapcastWorker covering more code paths."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from snapctrl.api.protocol import JsonRpcNotification
from snapctrl.core.worker import SnapcastWorker


class TestWorkerTimeouts:
    """Test worker timeout configuration."""

    def test_custom_timeout(self) -> None:
        """Test custom timeout is stored."""
        worker = SnapcastWorker("host", timeout=30.0)
        assert worker._timeout == 30.0

    def test_default_timeout(self) -> None:
        """Test default timeout is 10 seconds."""
        worker = SnapcastWorker("host")
        assert worker._timeout == 10.0


class TestWorkerClientMethods:
    """Test worker client-facing methods."""

    def test_set_client_latency_no_loop(self) -> None:
        """Test set_client_latency is safe without loop."""
        worker = SnapcastWorker("host")
        worker.set_client_latency("client1", 100)  # Should not crash

    def test_rename_client_no_loop(self) -> None:
        """Test rename_client is safe without loop."""
        worker = SnapcastWorker("host")
        worker.rename_client("client1", "New Name")  # Should not crash

    def test_rename_group_no_loop(self) -> None:
        """Test rename_group is safe without loop."""
        worker = SnapcastWorker("host")
        worker.rename_group("group1", "New Group Name")  # Should not crash

    def test_fetch_time_stats_no_loop(self) -> None:
        """Test fetch_time_stats is safe without loop."""
        worker = SnapcastWorker("host")
        worker.fetch_time_stats(["c1", "c2"])  # Should not crash


class TestWorkerEventHandlers:
    """Test worker event handler methods."""

    def test_on_disconnect_with_auto_reconnect(self) -> None:
        """Test _on_disconnect emits connection_lost when auto_reconnect enabled."""
        worker = SnapcastWorker("host")
        worker._auto_reconnect = True

        signals_received: list[str] = []
        worker.connection_lost.connect(lambda: signals_received.append("lost"))
        worker.disconnected.connect(lambda: signals_received.append("disconnected"))

        worker._on_disconnect()

        assert "lost" in signals_received
        assert "disconnected" not in signals_received

    def test_on_disconnect_without_auto_reconnect(self) -> None:
        """Test _on_disconnect emits disconnected when auto_reconnect disabled."""
        worker = SnapcastWorker("host")
        worker._auto_reconnect = False

        signals_received: list[str] = []
        worker.connection_lost.connect(lambda: signals_received.append("lost"))
        worker.disconnected.connect(lambda: signals_received.append("disconnected"))

        worker._on_disconnect()

        assert "lost" not in signals_received
        assert "disconnected" in signals_received

    def test_on_error_emits_signal(self) -> None:
        """Test _on_error emits error_occurred signal."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        test_error = ConnectionError("Test error")
        worker._on_error(test_error)

        assert len(errors) == 1
        assert errors[0] is test_error

    def test_on_notification_emits_signal(self) -> None:
        """Test _on_notification emits notification_received signal."""
        worker = SnapcastWorker("host")
        notifications: list[JsonRpcNotification] = []
        worker.notification_received.connect(notifications.append)

        notification = JsonRpcNotification(method="Client.OnVolumeChanged", params={})
        worker._on_notification(notification)

        assert len(notifications) == 1
        assert notifications[0] is notification


class TestWorkerAsyncMethods:
    """Test async helper methods with mocked client."""

    @pytest.mark.asyncio
    async def test_safe_set_client_mute_no_client(self) -> None:
        """Test _safe_set_client_mute returns early without client."""
        worker = SnapcastWorker("host")
        worker._client = None

        # Should not crash
        await worker._safe_set_client_mute("client1", True)

    @pytest.mark.asyncio
    async def test_safe_set_client_mute_not_connected(self) -> None:
        """Test _safe_set_client_mute returns early when not connected."""
        worker = SnapcastWorker("host")

        mock_client = MagicMock()
        mock_client.is_connected = False
        worker._client = mock_client

        await worker._safe_set_client_mute("client1", True)
        mock_client.set_client_mute.assert_not_called()

    @pytest.mark.asyncio
    async def test_safe_set_client_mute_emits_error(self) -> None:
        """Test _safe_set_client_mute emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_client_mute = AsyncMock(side_effect=ConnectionError("failed"))
        worker._client = mock_client

        await worker._safe_set_client_mute("client1", True)

        assert len(errors) == 1
        assert isinstance(errors[0], ConnectionError)

    @pytest.mark.asyncio
    async def test_safe_set_group_mute_no_client(self) -> None:
        """Test _safe_set_group_mute returns early without client."""
        worker = SnapcastWorker("host")
        await worker._safe_set_group_mute("group1", True)

    @pytest.mark.asyncio
    async def test_safe_set_group_mute_emits_error(self) -> None:
        """Test _safe_set_group_mute emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_group_mute = AsyncMock(side_effect=ValueError("bad"))
        worker._client = mock_client

        await worker._safe_set_group_mute("group1", True)

        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_safe_set_group_stream_no_client(self) -> None:
        """Test _safe_set_group_stream returns early without client."""
        worker = SnapcastWorker("host")
        await worker._safe_set_group_stream("group1", "stream1")

    @pytest.mark.asyncio
    async def test_safe_set_group_stream_emits_error(self) -> None:
        """Test _safe_set_group_stream emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_group_stream = AsyncMock(side_effect=RuntimeError("oops"))
        worker._client = mock_client

        await worker._safe_set_group_stream("group1", "stream1")

        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_safe_set_client_latency_no_client(self) -> None:
        """Test _safe_set_client_latency returns early without client."""
        worker = SnapcastWorker("host")
        await worker._safe_set_client_latency("client1", 50)

    @pytest.mark.asyncio
    async def test_safe_set_client_latency_success(self) -> None:
        """Test _safe_set_client_latency calls client method."""
        worker = SnapcastWorker("host")

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_client_latency = AsyncMock()
        mock_client.get_status = AsyncMock(return_value=None)
        worker._client = mock_client

        await worker._safe_set_client_latency("client1", 100)

        mock_client.set_client_latency.assert_called_once_with("client1", 100)

    @pytest.mark.asyncio
    async def test_safe_rename_client_no_client(self) -> None:
        """Test _safe_rename_client returns early without client."""
        worker = SnapcastWorker("host")
        await worker._safe_rename_client("client1", "Name")

    @pytest.mark.asyncio
    async def test_safe_rename_client_emits_error(self) -> None:
        """Test _safe_rename_client emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_client_name = AsyncMock(side_effect=OSError("failed"))
        worker._client = mock_client

        await worker._safe_rename_client("client1", "New Name")

        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_safe_rename_group_no_client(self) -> None:
        """Test _safe_rename_group returns early without client."""
        worker = SnapcastWorker("host")
        await worker._safe_rename_group("group1", "Name")

    @pytest.mark.asyncio
    async def test_safe_rename_group_emits_error(self) -> None:
        """Test _safe_rename_group emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_group_name = AsyncMock(side_effect=RuntimeError("fail"))
        worker._client = mock_client

        await worker._safe_rename_group("group1", "New Group")

        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_fetch_status_no_client(self) -> None:
        """Test _fetch_status returns early without client."""
        worker = SnapcastWorker("host")
        await worker._fetch_status()

    @pytest.mark.asyncio
    async def test_fetch_status_emits_error(self) -> None:
        """Test _fetch_status emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.get_status = AsyncMock(side_effect=ConnectionError("down"))
        worker._client = mock_client

        await worker._fetch_status()

        assert len(errors) == 1

    @pytest.mark.asyncio
    async def test_fetch_status_emits_state(self) -> None:
        """Test _fetch_status emits state_received signal."""
        worker = SnapcastWorker("host")
        states: list[Any] = []
        worker.state_received.connect(states.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_state = MagicMock()
        mock_client.get_status = AsyncMock(return_value=mock_state)
        worker._client = mock_client

        await worker._fetch_status()

        assert len(states) == 1
        assert states[0] is mock_state

    @pytest.mark.asyncio
    async def test_safe_fetch_time_stats_no_client(self) -> None:
        """Test _safe_fetch_time_stats returns early without client."""
        worker = SnapcastWorker("host")
        await worker._safe_fetch_time_stats(["c1"])

    @pytest.mark.asyncio
    async def test_safe_fetch_time_stats_success(self) -> None:
        """Test _safe_fetch_time_stats emits results."""
        worker = SnapcastWorker("host")
        results: list[dict[str, Any]] = []
        worker.time_stats_updated.connect(results.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.get_client_time_stats = AsyncMock(return_value={"latency_median_ms": 10})
        worker._client = mock_client

        await worker._safe_fetch_time_stats(["c1", "c2"])

        assert len(results) == 1
        assert "c1" in results[0]
        assert "c2" in results[0]

    @pytest.mark.asyncio
    async def test_safe_fetch_time_stats_handles_individual_errors(self) -> None:
        """Test _safe_fetch_time_stats continues on individual client errors."""
        worker = SnapcastWorker("host")
        results: list[dict[str, Any]] = []
        worker.time_stats_updated.connect(results.append)

        mock_client = MagicMock()
        mock_client.is_connected = True

        # First call fails, second succeeds
        mock_client.get_client_time_stats = AsyncMock(
            side_effect=[ValueError("fail"), {"latency_median_ms": 20}]
        )
        worker._client = mock_client

        await worker._safe_fetch_time_stats(["c1", "c2"])

        assert len(results) == 1
        assert "c1" not in results[0]
        assert "c2" in results[0]


class TestWorkerWithRunningLoop:
    """Test worker methods when loop is running."""

    def test_set_client_volume_schedules_coroutine(self) -> None:
        """Test set_client_volume schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.set_client_volume("c1", 50, False)
            mock_run.assert_called_once()

    def test_set_group_mute_schedules_coroutine(self) -> None:
        """Test set_group_mute schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.set_group_mute("g1", True)
            mock_run.assert_called_once()

    def test_request_status_schedules_coroutine(self) -> None:
        """Test request_status schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.request_status()
            mock_run.assert_called_once()


class TestWorkerTimeStatsSignal:
    """Test time_stats_updated signal."""

    def test_has_time_stats_signal(self) -> None:
        """Test worker has time_stats_updated signal."""
        worker = SnapcastWorker("host")
        assert hasattr(worker, "time_stats_updated")


class TestWorkerFetchTimeStats:
    """Test fetch_time_stats method scheduling."""

    def test_fetch_time_stats_schedules_coroutine(self) -> None:
        """Test fetch_time_stats schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.fetch_time_stats(["c1", "c2"])
            mock_run.assert_called_once()

    def test_fetch_time_stats_no_client(self) -> None:
        """Test fetch_time_stats does nothing without client."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = None  # No client

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.fetch_time_stats(["c1"])
            mock_run.assert_not_called()


class TestWorkerSafeFetchTimeStatsEdgeCases:
    """Additional edge case tests for _safe_fetch_time_stats."""

    @pytest.mark.asyncio
    async def test_safe_fetch_time_stats_disconnects_during_loop(self) -> None:
        """Test _safe_fetch_time_stats stops if client disconnects mid-loop."""
        worker = SnapcastWorker("host")
        results: list[dict[str, Any]] = []
        worker.time_stats_updated.connect(results.append)

        mock_client = MagicMock()
        # First check returns True, then returns False (disconnected)
        mock_client.is_connected = True

        call_count = [0]

        async def mock_get_stats(client_id: str) -> dict[str, Any] | None:
            call_count[0] += 1
            if call_count[0] == 1:
                return {"latency_median_ms": 10}
            # After first call, client "disconnects"
            mock_client.is_connected = False
            return {"latency_median_ms": 20}

        mock_client.get_client_time_stats = mock_get_stats
        worker._client = mock_client

        await worker._safe_fetch_time_stats(["c1", "c2", "c3"])

        # Should have some results (c1 at minimum)
        assert len(results) == 1
        assert "c1" in results[0]

    @pytest.mark.asyncio
    async def test_safe_fetch_time_stats_returns_none_stats(self) -> None:
        """Test _safe_fetch_time_stats skips None results."""
        worker = SnapcastWorker("host")
        results: list[dict[str, Any]] = []
        worker.time_stats_updated.connect(results.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        # First returns None, second returns data
        mock_client.get_client_time_stats = AsyncMock(side_effect=[None, {"latency_median_ms": 15}])
        worker._client = mock_client

        await worker._safe_fetch_time_stats(["c1", "c2"])

        assert len(results) == 1
        assert "c1" not in results[0]  # None result skipped
        assert "c2" in results[0]

    @pytest.mark.asyncio
    async def test_safe_fetch_time_stats_no_results(self) -> None:
        """Test _safe_fetch_time_stats doesn't emit when no results."""
        worker = SnapcastWorker("host")
        results: list[dict[str, Any]] = []
        worker.time_stats_updated.connect(results.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.get_client_time_stats = AsyncMock(return_value=None)
        worker._client = mock_client

        await worker._safe_fetch_time_stats(["c1"])

        # No signal emitted when no results
        assert len(results) == 0


class TestWorkerSetClientMuteScheduling:
    """Test set_client_mute method scheduling."""

    def test_set_client_mute_schedules_coroutine(self) -> None:
        """Test set_client_mute schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.set_client_mute("c1", True)
            mock_run.assert_called_once()

    def test_set_client_mute_no_loop(self) -> None:
        """Test set_client_mute is safe without loop."""
        worker = SnapcastWorker("host")
        worker.set_client_mute("c1", True)  # Should not crash


class TestWorkerSetGroupStreamScheduling:
    """Test set_group_stream method scheduling."""

    def test_set_group_stream_schedules_coroutine(self) -> None:
        """Test set_group_stream schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.set_group_stream("g1", "stream1")
            mock_run.assert_called_once()

    def test_set_group_stream_no_loop(self) -> None:
        """Test set_group_stream is safe without loop."""
        worker = SnapcastWorker("host")
        worker.set_group_stream("g1", "stream1")  # Should not crash


class TestWorkerSetClientLatencyScheduling:
    """Test set_client_latency method scheduling."""

    def test_set_client_latency_schedules_coroutine(self) -> None:
        """Test set_client_latency schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.set_client_latency("c1", 100)
            mock_run.assert_called_once()


class TestWorkerRenameClientScheduling:
    """Test rename_client method scheduling."""

    def test_rename_client_schedules_coroutine(self) -> None:
        """Test rename_client schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.rename_client("c1", "New Name")
            mock_run.assert_called_once()


class TestWorkerRenameGroupScheduling:
    """Test rename_group method scheduling."""

    def test_rename_group_schedules_coroutine(self) -> None:
        """Test rename_group schedules coroutine when loop running."""
        worker = SnapcastWorker("host")
        mock_loop = MagicMock()
        mock_loop.is_running.return_value = True
        worker._loop = mock_loop
        worker._client = MagicMock()

        with patch("asyncio.run_coroutine_threadsafe") as mock_run:
            worker.rename_group("g1", "New Group")
            mock_run.assert_called_once()


class TestWorkerSafeSetGroupStreamSuccess:
    """Test _safe_set_group_stream success path."""

    @pytest.mark.asyncio
    async def test_safe_set_group_stream_success(self) -> None:
        """Test _safe_set_group_stream calls client and fetches status."""
        worker = SnapcastWorker("host")
        states: list[Any] = []
        worker.state_received.connect(states.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_group_stream = AsyncMock()
        mock_state = MagicMock()
        mock_client.get_status = AsyncMock(return_value=mock_state)
        worker._client = mock_client

        await worker._safe_set_group_stream("g1", "stream1")

        mock_client.set_group_stream.assert_called_once_with("g1", "stream1")
        mock_client.get_status.assert_called_once()  # Refresh status
        assert len(states) == 1


class TestWorkerSafeSetClientLatencySuccess:
    """Test _safe_set_client_latency success path."""

    @pytest.mark.asyncio
    async def test_safe_set_client_latency_emits_error(self) -> None:
        """Test _safe_set_client_latency emits error on exception."""
        worker = SnapcastWorker("host")
        errors: list[Exception] = []
        worker.error_occurred.connect(errors.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_client_latency = AsyncMock(side_effect=ValueError("bad"))
        worker._client = mock_client

        await worker._safe_set_client_latency("c1", 100)

        assert len(errors) == 1


class TestWorkerSafeRenameClientSuccess:
    """Test _safe_rename_client success path."""

    @pytest.mark.asyncio
    async def test_safe_rename_client_success(self) -> None:
        """Test _safe_rename_client calls client and fetches status."""
        worker = SnapcastWorker("host")
        states: list[Any] = []
        worker.state_received.connect(states.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_client_name = AsyncMock()
        mock_state = MagicMock()
        mock_client.get_status = AsyncMock(return_value=mock_state)
        worker._client = mock_client

        await worker._safe_rename_client("c1", "New Name")

        mock_client.set_client_name.assert_called_once_with("c1", "New Name")
        mock_client.get_status.assert_called_once()  # Refresh status
        assert len(states) == 1


class TestWorkerSafeRenameGroupSuccess:
    """Test _safe_rename_group success path."""

    @pytest.mark.asyncio
    async def test_safe_rename_group_success(self) -> None:
        """Test _safe_rename_group calls client and fetches status."""
        worker = SnapcastWorker("host")
        states: list[Any] = []
        worker.state_received.connect(states.append)

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_group_name = AsyncMock()
        mock_state = MagicMock()
        mock_client.get_status = AsyncMock(return_value=mock_state)
        worker._client = mock_client

        await worker._safe_rename_group("g1", "New Group")

        mock_client.set_group_name.assert_called_once_with("g1", "New Group")
        mock_client.get_status.assert_called_once()  # Refresh status
        assert len(states) == 1


class TestWorkerSafeSetClientMuteSuccess:
    """Test _safe_set_client_mute success path."""

    @pytest.mark.asyncio
    async def test_safe_set_client_mute_success(self) -> None:
        """Test _safe_set_client_mute calls client method."""
        worker = SnapcastWorker("host")

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_client_mute = AsyncMock()
        worker._client = mock_client

        await worker._safe_set_client_mute("c1", True)

        mock_client.set_client_mute.assert_called_once_with("c1", True)


class TestWorkerSafeSetGroupMuteSuccess:
    """Test _safe_set_group_mute success path."""

    @pytest.mark.asyncio
    async def test_safe_set_group_mute_success(self) -> None:
        """Test _safe_set_group_mute calls client method."""
        worker = SnapcastWorker("host")

        mock_client = MagicMock()
        mock_client.is_connected = True
        mock_client.set_group_mute = AsyncMock()
        worker._client = mock_client

        await worker._safe_set_group_mute("g1", False)

        mock_client.set_group_mute.assert_called_once_with("g1", False)
