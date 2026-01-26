"""Test fixtures for snapcast_mvp tests."""

import asyncio
import json
from collections.abc import AsyncGenerator, Generator

import pytest

# Conditionally import websockets only if actually needed
# (skip for CI environments without Qt/websockets support)
try:
    import websockets
    from websockets.server import WebSocketServerProtocol
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

from snapcast_mvp.api.client import SnapcastClient


@pytest.fixture
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def mock_server() -> AsyncGenerator[tuple[str, int], None]:
    """Fixture providing a mock WebSocket server.

    Returns:
        Tuple of (host, port) for the test server.
    """
    if not HAS_WEBSOCKETS:
        pytest.skip("websockets not available in this environment")

    async def handler(websocket: WebSocketServerProtocol) -> None:
        """Handle WebSocket connections."""
        async for message in websocket:
            try:
                data = json.loads(message)
                method = data.get("method", "")

                # Handle Server.GetStatus
                if method == "Server.GetStatus":
                    response = {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": _mock_status_response(),
                    }
                    await websocket.send(json.dumps(response))

                # Handle Client.SetVolume, Group.SetMute, Group.SetStream
                elif method in {
                    "Client.SetVolume",
                    "Group.SetMute",
                    "Group.SetStream",
                }:
                    response = {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": "OK",
                    }
                    await websocket.send(json.dumps(response))

                # Handle Server.GetRPCVersion
                elif method == "Server.GetRPCVersion":
                    response = {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "result": {"major": 2, "minor": 1},
                    }
                    await websocket.send(json.dumps(response))

                # Unknown method
                else:
                    response = {
                        "jsonrpc": "2.0",
                        "id": data.get("id"),
                        "error": {
                            "code": -32601,
                            "message": "Method not found",
                        },
                    }
                    await websocket.send(json.dumps(response))

            except Exception:
                # Send error response
                response = {
                    "jsonrpc": "2.0",
                    "id": data.get("id", 1),
                    "error": {
                        "code": -32700,
                        "message": "Parse error",
                    },
                }
                await websocket.send(json.dumps(response))

    # Start server on random port
    async with websockets.serve(handler, "127.0.0.1", 0) as server:
        # Get the assigned port
        port = server.sockets[0].getsockname()[1] if server.sockets else 8765
        yield "127.0.0.1", port


def _mock_status_response() -> dict:
    """Return a mock Server.GetStatus response."""
    return {
        "server": {
            "host": "snapcast-test",
            "port": 1704,
            "version": "0.27.0",
            "mac": "00:11:22:33:44:55",
        },
        "groups": [
            {
                "id": "group-1",
                "name": "Default",
                "stream_id": "stream-1",
                "muted": False,
                "clients": ["client-1", "client-2"],
            },
            {
                "id": "group-2",
                "name": "Bedroom",
                "stream_id": "stream-1",
                "muted": False,
                "clients": ["client-3"],
            },
        ],
        "clients": [
            {
                "id": "client-1",
                "host": "192.168.1.10",
                "connected": True,
                "config": {
                    "name": "Living Room",
                    "mac": "AA:BB:CC:DD:EE:01",
                    "volume": {"percent": 75, "muted": False},
                    "latency": 0,
                    "snapclient": {"version": "0.27.0"},
                },
            },
            {
                "id": "client-2",
                "host": "192.168.1.11",
                "connected": True,
                "config": {
                    "name": "Kitchen",
                    "mac": "AA:BB:CC:DD:EE:02",
                    "volume": {"percent": 50, "muted": True},
                    "latency": 100,
                    "snapclient": {"version": "0.27.0"},
                },
            },
            {
                "id": "client-3",
                "host": "192.168.1.12",
                "connected": False,
                "config": {
                    "name": "Bedroom",
                    "mac": "AA:BB:CC:DD:EE:03",
                    "volume": {"percent": 30, "muted": False},
                    "latency": 0,
                    "snapclient": {"version": "0.26.0"},
                },
            },
        ],
        "streams": [
            {
                "id": "stream-1",
                "status": {
                    "title": "Spotify",
                    "playback": "playing",
                    "contentType": "spotify",
                },
            },
            {
                "id": "stream-2",
                "status": {
                    "title": "AirPlay",
                    "playback": "idle",
                    "contentType": "airplay",
                },
            },
        ],
    }


@pytest.fixture
def mock_status_response() -> dict:
    """Return a mock Server.GetStatus response dict."""
    return _mock_status_response()


@pytest.fixture
async def connected_client(
    mock_server: tuple[str, int],
) -> AsyncGenerator[SnapcastClient, None]:
    """Fixture providing a connected SnapcastClient.

    The client is connected to the mock server.
    """
    if not HAS_WEBSOCKETS:
        pytest.skip("websockets not available in this environment")

    host, port = mock_server
    url = f"ws://{host}:{port}/jsonrpc"

    client = SnapcastClient(url)
    await client.connect()

    yield client

    await client.disconnect()
