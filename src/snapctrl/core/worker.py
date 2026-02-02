"""QThread worker for running async SnapcastClient in a Qt application.

Qt widgets must run in the main thread, but the SnapcastClient uses asyncio.
This worker runs the asyncio event loop in a background thread and bridges
events to the main thread via Qt signals.
"""

import asyncio
import logging

from PySide6.QtCore import QThread, Signal

from snapctrl.api.client import SnapcastClient
from snapctrl.api.protocol import JsonRpcNotification

logger = logging.getLogger(__name__)


class SnapcastWorker(QThread):
    """Background thread worker for Snapcast TCP client.

    Runs the async SnapcastClient in a QThread so the main Qt thread
    stays responsive. Emits Qt signals when events occur.

    Example:
        worker = SnapcastWorker("192.168.1.100", 1705)
        worker.connected.connect(lambda: print("Connected!"))
        worker.state_received.connect(lambda state: print(f"State: {state}"))
        worker.error.connect(lambda e: print(f"Error: {e}"))
        worker.start()
    """

    # Connection state signals
    connected = Signal()  # Successfully connected to server
    disconnected = Signal()  # Disconnected from server
    connection_lost = Signal()  # Unexpected disconnection

    # Data signals
    state_received = Signal(object)  # ServerState object
    notification_received = Signal(object)  # JsonRpcNotification

    # Time stats signal
    time_stats_updated = Signal(dict)  # {client_id: {latency_median_ms, ...}}

    # Error signal
    error_occurred = Signal(object)  # Exception

    def __init__(self, host: str, port: int = 1705, timeout: float = 10.0) -> None:
        """Initialize the worker.

        Args:
            host: Server hostname or IP.
            port: TCP port (default 1705).
            timeout: Connection timeout in seconds.
        """
        super().__init__()
        self._host = host
        self._port = port
        self._timeout = timeout
        self._client: SnapcastClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._should_run = True
        self._auto_reconnect = True
        self._reconnect_delay = 2.0  # Initial reconnect delay

    @property
    def host(self) -> str:
        """Return server host."""
        return self._host

    @property
    def port(self) -> int:
        """Return server port."""
        return self._port

    @property
    def is_connected(self) -> bool:
        """Return True if client is connected."""
        return self._client is not None and self._client.is_connected

    def stop(self) -> None:
        """Signal the worker to stop (called from main thread)."""
        self._should_run = False
        if self._client and self._loop and self._loop.is_running():
            # Schedule disconnect on the event loop
            asyncio.run_coroutine_threadsafe(self._client.disconnect(), self._loop)

    def request_status(self) -> None:
        """Request a status update from the server.

        Thread-safe call from main thread.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(self._fetch_status(), self._loop)

    def fetch_time_stats(self, client_ids: list[str]) -> None:
        """Fetch server-side latency stats for connected clients.

        Thread-safe call from main thread.

        Args:
            client_ids: List of connected client IDs to query.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_fetch_time_stats(client_ids),
                self._loop,
            )

    async def _safe_fetch_time_stats(self, client_ids: list[str]) -> None:
        """Fetch time stats with per-client error handling."""
        if not self._client or not self._client.is_connected:
            return
        results: dict[str, dict[str, object]] = {}
        for client_id in client_ids:
            if not self._client.is_connected:
                break
            try:
                stats = await self._client.get_client_time_stats(client_id)
                if stats:
                    results[client_id] = stats
            except Exception:  # noqa: BLE001
                logger.debug("Failed to fetch time stats for %s", client_id, exc_info=True)
                continue
        if results:
            self.time_stats_updated.emit(results)

    def set_client_volume(self, client_id: str, volume: int, muted: bool) -> None:
        """Set client volume.

        Thread-safe call from main thread.

        Args:
            client_id: ID of the client.
            volume: Volume 0-100.
            muted: Whether muted.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._client.set_client_volume(client_id, volume, muted),
                self._loop,
            )

    def set_client_mute(self, client_id: str, muted: bool) -> None:
        """Set client mute state only (without changing volume).

        Thread-safe call from main thread. Errors are emitted via error_occurred signal.

        Args:
            client_id: ID of the client.
            muted: Whether muted.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_set_client_mute(client_id, muted),
                self._loop,
            )

    async def _safe_set_client_mute(self, client_id: str, muted: bool) -> None:
        """Set client mute with error handling."""
        if not self._client or not self._client.is_connected:
            return
        try:
            await self._client.set_client_mute(client_id, muted)
        except Exception as e:
            self.error_occurred.emit(e)

    def set_group_mute(self, group_id: str, muted: bool) -> None:
        """Set group mute state.

        Thread-safe call from main thread.

        Args:
            group_id: ID of the group.
            muted: Whether muted.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_set_group_mute(group_id, muted),
                self._loop,
            )

    async def _safe_set_group_mute(self, group_id: str, muted: bool) -> None:
        """Set group mute with error handling."""
        if not self._client or not self._client.is_connected:
            return
        try:
            await self._client.set_group_mute(group_id, muted)
        except Exception as e:
            self.error_occurred.emit(e)

    def set_group_stream(self, group_id: str, stream_id: str) -> None:
        """Set group audio stream.

        Thread-safe call from main thread.

        Args:
            group_id: ID of the group.
            stream_id: ID of the stream.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_set_group_stream(group_id, stream_id),
                self._loop,
            )

    async def _safe_set_group_stream(self, group_id: str, stream_id: str) -> None:
        """Set group stream with error handling and status refresh."""
        if not self._client or not self._client.is_connected:
            return
        try:
            await self._client.set_group_stream(group_id, stream_id)
            # Refresh status after changing stream
            await self._fetch_status()
        except Exception as e:
            self.error_occurred.emit(e)

    def set_client_latency(self, client_id: str, latency: int) -> None:
        """Set client latency offset.

        Thread-safe call from main thread.

        Args:
            client_id: ID of the client.
            latency: Latency offset in milliseconds.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_set_client_latency(client_id, latency),
                self._loop,
            )

    async def _safe_set_client_latency(self, client_id: str, latency: int) -> None:
        """Set client latency with error handling and status refresh."""
        if not self._client or not self._client.is_connected:
            return
        try:
            await self._client.set_client_latency(client_id, latency)
            await self._fetch_status()
        except Exception as e:
            self.error_occurred.emit(e)

    def rename_client(self, client_id: str, name: str) -> None:
        """Rename a client.

        Thread-safe call from main thread.

        Args:
            client_id: ID of the client.
            name: New display name.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_rename_client(client_id, name),
                self._loop,
            )

    async def _safe_rename_client(self, client_id: str, name: str) -> None:
        """Rename client with error handling and status refresh."""
        if not self._client or not self._client.is_connected:
            return
        try:
            await self._client.set_client_name(client_id, name)
            await self._fetch_status()
        except Exception as e:
            self.error_occurred.emit(e)

    def rename_group(self, group_id: str, name: str) -> None:
        """Rename a group.

        Thread-safe call from main thread.

        Args:
            group_id: ID of the group.
            name: New display name.
        """
        if self._loop and self._loop.is_running() and self._client:
            asyncio.run_coroutine_threadsafe(
                self._safe_rename_group(group_id, name),
                self._loop,
            )

    async def _safe_rename_group(self, group_id: str, name: str) -> None:
        """Rename group with error handling and status refresh."""
        if not self._client or not self._client.is_connected:
            return
        try:
            await self._client.set_group_name(group_id, name)
            await self._fetch_status()
        except Exception as e:
            self.error_occurred.emit(e)

    def run(self) -> None:
        """Run the worker thread (entry point)."""
        # Create new event loop for this thread
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        try:
            # Run connection loop
            self._loop.run_until_complete(self._connection_loop())
        except Exception as e:
            self.error_occurred.emit(e)
        finally:
            # Clean up
            if self._client:
                self._loop.run_until_complete(self._client.disconnect())
            self._loop.close()
            self._loop = None
            self._client = None

    async def _connection_loop(self) -> None:
        """Main connection loop with auto-reconnect."""
        reconnect_delay = self._reconnect_delay

        while self._should_run:
            try:
                # Create client and connect
                self._client = SnapcastClient(
                    self._host,
                    self._port,
                    self._timeout,
                )

                # Set up event handlers using public API
                self._client.set_event_handlers(
                    on_notification=self._on_notification,
                    on_disconnect=self._on_disconnect,
                    on_error=self._on_error,
                )

                await self._client.connect()

                # Connected successfully
                self.connected.emit()
                reconnect_delay = self._reconnect_delay  # Reset delay

                # Fetch initial status
                await self._fetch_status()

                # Keep connection alive until disconnected
                while self._should_run and self._client.is_connected:
                    await asyncio.sleep(0.5)

                # Normal exit
                if not self._should_run:
                    break

            except (OSError, ConnectionError) as e:
                self.error_occurred.emit(e)
                if not self._should_run:
                    break

                # Auto-reconnect with backoff
                if self._auto_reconnect and self._should_run:
                    self.disconnected.emit()
                    await asyncio.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, 30.0)  # Max 30s
                else:
                    break

    async def _fetch_status(self) -> None:
        """Fetch server status and emit signal."""
        if not self._client or not self._client.is_connected:
            return

        try:
            state = await self._client.get_status()
            self.state_received.emit(state)
        except Exception as e:
            self.error_occurred.emit(e)

    def _on_disconnect(self) -> None:
        """Handle client disconnect."""
        if self._auto_reconnect:
            self.connection_lost.emit()
        else:
            self.disconnected.emit()

    def _on_error(self, error: Exception) -> None:
        """Handle client error."""
        self.error_occurred.emit(error)

    def _on_notification(self, notification: JsonRpcNotification) -> None:
        """Handle server notification."""
        self.notification_received.emit(notification)
