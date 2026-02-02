"""Snapcast JSON-RPC API client over TCP.

Snapcast uses raw TCP sockets with JSON-RPC, not WebSocket.
Each message is a JSON-RPC request/response delimited by newlines.
"""

import asyncio
import json
import logging
from collections.abc import Callable
from contextlib import suppress
from typing import Any, cast

from snapctrl.api.protocol import (
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
)
from snapctrl.models.client import Client
from snapctrl.models.group import Group
from snapctrl.models.server import Server
from snapctrl.models.server_state import ServerState
from snapctrl.models.source import Source, SourceStatus

logger = logging.getLogger(__name__)

# Type aliases for event handlers
ConnectionHandler = Callable[[], None]
NotificationHandler = Callable[[JsonRpcNotification], None]
ErrorHandler = Callable[[Exception], None]


class SnapcastClient:
    """Async TCP client for Snapcast JSON-RPC API.

    Snapcast uses raw TCP sockets (not WebSocket) for JSON-RPC communication.
    Each message is a JSON object delimited by newlines.

    Example:
        async with SnapcastClient("192.168.1.100", 1705) as client:
            status = await client.get_status()
            print(f"Connected to {status.server.host}")
    """

    _DEFAULT_TIMEOUT: float = 10.0
    _READ_CHUNK_SIZE: int = 4096

    def __init__(
        self,
        host: str,
        port: int = 1705,
        timeout: float = _DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize the client.

        Args:
            host: Server hostname or IP address.
            port: TCP port (default 1705).
            timeout: Connection/operation timeout in seconds.
        """
        self._host = host
        self._port = port
        self._timeout = timeout
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._request_id: int = 0
        self._pending: dict[int, asyncio.Future[JsonRpcResponse]] = {}
        self._connected: bool = False
        self._receive_task: asyncio.Task[None] | None = None

        # Event handlers
        self._on_notification: NotificationHandler | None = None
        self._on_disconnect: ConnectionHandler | None = None
        self._on_error: ErrorHandler | None = None

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
        """Return True if connected to server."""
        return self._connected and self._reader is not None

    def set_event_handlers(
        self,
        on_notification: NotificationHandler | None = None,
        on_disconnect: ConnectionHandler | None = None,
        on_error: ErrorHandler | None = None,
    ) -> None:
        """Set event handlers for client events.

        Args:
            on_notification: Handler for JSON-RPC notifications.
            on_disconnect: Handler for disconnect events.
            on_error: Handler for errors.
        """
        self._on_notification = on_notification
        self._on_disconnect = on_disconnect
        self._on_error = on_error

    async def __aenter__(self) -> "SnapcastClient":
        """Enter async context (connect)."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Exit async context (disconnect)."""
        await self.disconnect()

    async def connect(self) -> None:
        """Connect to the Snapcast server.

        Raises:
            ConnectionError: If connection fails.
            TimeoutError: If connection times out.
        """
        if self._connected:
            return

        try:
            # Use larger buffer limit to handle big Server.GetStatus responses
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port, limit=1024 * 1024),
                timeout=self._timeout,
            )
            self._connected = True
            self._receive_task = asyncio.create_task(self._receive_loop())
        except (OSError, TimeoutError) as e:
            self._connected = False
            self._reader = None
            self._writer = None
            raise ConnectionError(f"Failed to connect to {self._host}:{self._port}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the server."""
        self._connected = False

        # Cancel receive task
        if self._receive_task:
            self._receive_task.cancel()
            with suppress(asyncio.CancelledError):
                await self._receive_task
            self._receive_task = None

        # Close socket
        if self._writer:
            try:
                self._writer.close()
                await asyncio.wait_for(self._writer.wait_closed(), timeout=1.0)
            except (OSError, TimeoutError, asyncio.CancelledError):
                pass
            self._writer = None
        self._reader = None

        # Resolve pending requests with error
        for future in self._pending.values():
            if not future.done():
                future.set_exception(ConnectionError("Connection closed"))
        self._pending.clear()

    async def _receive_loop(self) -> None:
        """Background task to receive and dispatch messages."""
        if self._reader is None:
            return

        try:
            while self._connected:
                try:
                    # Read a line (JSON-RPC messages are newline-delimited)
                    # Buffer limit is set in open_connection() to handle large responses
                    line = await asyncio.wait_for(
                        self._reader.readline(),
                        timeout=self._timeout,
                    )
                    if not line:
                        # Server closed connection
                        break

                    message = line.decode("utf-8").strip()
                    if not message:
                        continue

                    data = json.loads(message)
                    await self._handle_message(data)

                except TimeoutError:
                    # No data for timeout period - check if still connected
                    if not self._connected:
                        break
                except asyncio.IncompleteReadError:
                    # Server closed connection mid-read
                    break
                except asyncio.LimitOverrunError as e:
                    # Message too large even with increased limit
                    self._emit_error(e)
                    continue
                except json.JSONDecodeError as e:
                    self._emit_error(e)
                except Exception as e:
                    self._emit_error(e)
                    break

        except asyncio.CancelledError:
            pass
        finally:
            self._connected = False
            self._emit_disconnect()

    async def _handle_message(self, data: dict[str, Any]) -> None:
        """Handle an incoming message."""
        # Check for notification (no 'id' but has 'method')
        if "id" not in data and "method" in data:
            notification = JsonRpcNotification.from_dict(data)
            self._emit_notification(notification)
            return

        # Handle response
        response_id = data.get("id")
        if isinstance(response_id, int):
            response = JsonRpcResponse.from_dict(data)
            future = self._pending.pop(response_id, None)
            if future and not future.done():
                future.set_result(response)

    def _emit_notification(self, notification: JsonRpcNotification) -> None:
        """Emit notification to handler."""
        if self._on_notification:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon(self._on_notification, notification)
            except RuntimeError:
                # No event loop running - this happens during shutdown
                logger.debug("Cannot emit notification: no event loop running")

    def _emit_disconnect(self) -> None:
        """Emit disconnect to handler."""
        if self._on_disconnect:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon(self._on_disconnect)
            except RuntimeError:
                # No event loop running - this happens during shutdown
                logger.debug("Cannot emit disconnect: no event loop running")

    def _emit_error(self, error: Exception) -> None:
        """Emit error to handler."""
        if self._on_error:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.call_soon(self._on_error, error)
            except RuntimeError:
                # No event loop running - this happens during shutdown
                logger.debug("Cannot emit error: no event loop running")

    def _next_id(self) -> int:
        """Generate next request ID."""
        self._request_id += 1
        return self._request_id

    async def _send(self, request: JsonRpcRequest) -> JsonRpcResponse:
        """Send a request and wait for response.

        Args:
            request: The JSON-RPC request to send.

        Returns:
            The JSON-RPC response.

        Raises:
            ConnectionError: If not connected.
            JsonRpcError: If server returns an error.
        """
        if not self.is_connected or self._writer is None:
            raise ConnectionError("Not connected to server")

        # Extract int ID for pending dict
        req_id = request.id if isinstance(request.id, int) else self._next_id()

        # Create future for response
        future: asyncio.Future[JsonRpcResponse] = asyncio.Future()
        self._pending[req_id] = future

        try:
            # Send request (JSON-RPC over TCP, newline delimited)
            message = json.dumps(request.to_dict()) + "\n"
            self._writer.write(message.encode("utf-8"))
            await asyncio.wait_for(self._writer.drain(), timeout=self._timeout)

            # Wait for response
            response = await asyncio.wait_for(future, timeout=self._timeout)

            # Check for error - include request ID for debugging
            if not response.is_success:
                err = response.error or JsonRpcError(-1, "Unknown error")
                raise RuntimeError(f"Request {req_id} failed: {err}")

            return response
        except TimeoutError:
            self._pending.pop(req_id, None)
            raise ConnectionError(f"Request {req_id} timed out") from None
        except Exception:
            self._pending.pop(req_id, None)
            raise

    async def call(
        self,
        method: str,
        params: dict[str, Any] | list[Any] | None = None,
    ) -> Any:
        """Call a JSON-RPC method.

        Args:
            method: Method name.
            params: Method parameters.

        Returns:
            The method result.

        Raises:
            ConnectionError: If not connected or request times out.
            JsonRpcError: If server returns an error.
        """
        request = JsonRpcRequest.call(method, params, self._next_id())
        response = await self._send(request)
        return response.result

    # Specific Snapcast API methods

    async def get_status(self) -> ServerState:
        """Get server status (Server.GetStatus).

        Returns:
            ServerState with current server state.

        Raises:
            ConnectionError: If not connected or request times out.
            JsonRpcError: If server returns an error.
        """
        result = await self.call("Server.GetStatus")
        return _parse_server_status(result)

    async def get_rpc_version(self) -> dict[str, Any]:
        """Get JSON-RPC version (Server.GetRPCVersion).

        Returns:
            Dict with major/minor version info.
        """
        return await self.call("Server.GetRPCVersion")

    async def set_client_volume(
        self,
        client_id: str,
        volume: int,
        muted: bool = False,
    ) -> None:
        """Set client volume (Client.SetVolume).

        Args:
            client_id: ID of the client.
            volume: Volume 0-100.
            muted: Whether client is muted.
        """
        await self.call(
            "Client.SetVolume",
            {
                "id": client_id,
                "volume": {"percent": volume, "muted": muted},
            },
        )

    async def set_client_mute(self, client_id: str, muted: bool) -> None:
        """Set client mute state only (Client.SetVolume with muted only).

        This sends only the muted flag without changing the volume value.
        Use this when toggling mute to avoid sending redundant volume data.

        Args:
            client_id: ID of the client.
            muted: Whether client is muted.
        """
        await self.call(
            "Client.SetVolume",
            {
                "id": client_id,
                "volume": {"muted": muted},
            },
        )

    async def set_group_mute(self, group_id: str, muted: bool) -> None:
        """Set group mute state (Group.SetMute).

        Args:
            group_id: ID of the group.
            muted: Whether to mute the group.
        """
        await self.call(
            "Group.SetMute",
            {"id": group_id, "mute": muted},
        )

    async def set_group_stream(self, group_id: str, stream_id: str) -> None:
        """Set group audio stream (Group.SetStream).

        Args:
            group_id: ID of the group.
            stream_id: ID of the stream to switch to.
        """
        await self.call(
            "Group.SetStream",
            {"id": group_id, "stream_id": stream_id},
        )

    async def set_client_name(self, client_id: str, name: str) -> None:
        """Set client name (Client.SetName).

        Args:
            client_id: ID of the client.
            name: New display name.
        """
        await self.call(
            "Client.SetName",
            {"id": client_id, "name": name},
        )

    async def set_client_latency(self, client_id: str, latency: int) -> None:
        """Set client latency offset (Client.SetLatency).

        Args:
            client_id: ID of the client.
            latency: Latency offset in milliseconds (-1000 to 1000).
        """
        await self.call(
            "Client.SetLatency",
            {"id": client_id, "latency": latency},
        )

    _TIME_STATS_KEYS = {"latency_median_ms", "latency_p95_ms", "jitter_ms", "samples"}

    async def get_client_time_stats(
        self,
        client_id: str,
    ) -> dict[str, Any]:
        """Get server-measured latency stats (Client.GetTimeStats).

        Requires a Snapcast server that supports this endpoint (fork).
        Returns empty dict if the server doesn't support it.

        Args:
            client_id: ID of the client.

        Returns:
            Dict with latency_median_ms, latency_p95_ms, jitter_ms,
            samples, suggested_buffer_ms. Empty dict on error.
        """
        try:
            result = await self.call(
                "Client.GetTimeStats",
                {"id": client_id},
            )
            if not isinstance(result, dict):
                return {}
            typed = cast(dict[str, Any], result)
            if not self._TIME_STATS_KEYS.issubset(typed):
                logger.debug("GetTimeStats missing keys: %s", typed.keys())
                return {}
            return typed
        except RuntimeError as e:
            if "method not found" in str(e).lower():
                logger.debug("Server does not support Client.GetTimeStats")
            else:
                logger.warning("GetTimeStats failed for %s: %s", client_id, e)
            return {}
        except ConnectionError:
            return {}

    async def set_group_name(self, group_id: str, name: str) -> None:
        """Set group name (Group.SetName).

        Args:
            group_id: ID of the group.
            name: New display name.
        """
        await self.call(
            "Group.SetName",
            {"id": group_id, "name": name},
        )


def _parse_server_status(data: dict[str, Any]) -> ServerState:
    """Parse Server.GetStatus response into ServerState.

    Snapcast's actual response structure:
    {
      "server": {
        "groups": [{ "id": "...", "name": "...", "clients": [...] }],
        "server": {
          "snapserver": {"version": "..."},
          "host": {"name": "...", "ip": "...", "mac": "..."}
        },
        "streams": [...]
      }
    }

    Args:
        data: Raw response data from server.

    Returns:
        ServerState with parsed models.
    """
    # Navigate to the nested structure
    server_data = data.get("server", {})
    inner_server = server_data.get("server", {})
    snapserver_info = inner_server.get("snapserver", {})
    host_info = inner_server.get("host", {})

    # Extract server info
    server = Server(
        name=host_info.get("name", "Unknown"),
        host=host_info.get("ip", "") or host_info.get("name", ""),
        port=1705,
    )

    # Parse groups (nested under server.groups)
    groups_data = server_data.get("groups", [])
    groups: list[Group] = []

    for g in groups_data:
        # Extract client IDs from the clients array within the group
        clients_data = g.get("clients", [])
        client_ids = [c.get("id", "") for c in clients_data]

        groups.append(
            Group(
                id=g.get("id", ""),
                name=g.get("name", ""),
                stream_id=g.get("stream_id", ""),
                muted=g.get("muted", False),
                client_ids=client_ids,
            )
        )

    # Parse clients (flatten from all groups)
    clients: list[Client] = []
    for g in groups_data:
        for c in g.get("clients", []):
            config = c.get("config", {})
            host = c.get("host", {})
            snapclient = c.get("snapclient", {})
            last_seen = c.get("lastSeen", {})

            clients.append(
                Client(
                    id=c.get("id", ""),
                    host=host.get("ip", ""),
                    name=config.get("name", ""),
                    mac=host.get("mac", ""),
                    volume=config.get("volume", {}).get("percent", 50),
                    muted=config.get("volume", {}).get("muted", False),
                    connected=c.get("connected", True),
                    latency=config.get("latency", 0),
                    snapclient_version=snapclient.get("version", ""),
                    last_seen_sec=last_seen.get("sec", 0),
                    last_seen_usec=last_seen.get("usec", 0),
                    host_os=host.get("os", ""),
                    host_arch=host.get("arch", ""),
                    host_name=host.get("name", ""),
                )
            )

    # Parse streams (nested under server.streams)
    streams_data = server_data.get("streams", [])
    sources: list[Source] = []

    for s in streams_data:
        status_str = SourceStatus.from_string(s.get("status", "idle"))
        uri = s.get("uri", {})
        query = uri.get("query", {})
        properties = s.get("properties", {})

        # Codec can come from properties (modern) or query (legacy)
        codec = properties.get("codec", {}).get("name", "") or query.get("codec", "")

        # Extract metadata (track info) if available
        metadata_raw = properties.get("metadata")
        meta_title = ""
        meta_artist = ""
        meta_album = ""
        meta_art_url = ""

        if isinstance(metadata_raw, dict):
            metadata = cast(dict[str, Any], metadata_raw)
            # Title
            title_val = metadata.get("title")
            if title_val is not None:
                meta_title = str(title_val)

            # Artist (can be list or string)
            artist_val = metadata.get("artist")
            if isinstance(artist_val, list):
                artist_list = cast(list[Any], artist_val)
                meta_artist = ", ".join(str(x) for x in artist_list)
            elif artist_val is not None:
                meta_artist = str(artist_val)

            # Album
            album_val = metadata.get("album")
            if album_val is not None:
                meta_album = str(album_val)

            # Art URL
            art_url_val = metadata.get("artUrl")
            if art_url_val is not None:
                meta_art_url = str(art_url_val)

        sources.append(
            Source(
                id=s.get("id", ""),
                name=query.get("name", s.get("id", "")),
                status=status_str,
                stream_type=codec or "unknown",  # Keep backward compatibility
                codec=codec,
                sample_format=properties.get("sampleFormat", query.get("sampleformat", "")),
                uri_scheme=uri.get("scheme", ""),
                uri_raw=uri.get("raw", ""),
                meta_title=meta_title,
                meta_artist=meta_artist,
                meta_album=meta_album,
                meta_art_url=meta_art_url,
            )
        )

    return ServerState(
        server=server,
        groups=groups,
        clients=clients,
        sources=sources,
        connected=True,
        version=snapserver_info.get("version", ""),
        host=host_info.get("name", ""),
        mac=host_info.get("mac", ""),
    )
