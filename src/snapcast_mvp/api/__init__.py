"""API client for Snapcast JSON-RPC over WebSocket."""

from snapcast_mvp.api.client import SnapcastClient
from snapcast_mvp.api.protocol import (
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
)

__all__ = [
    "SnapcastClient",
    "JsonRpcRequest",
    "JsonRpcResponse",
    "JsonRpcNotification",
    "JsonRpcError",
]
