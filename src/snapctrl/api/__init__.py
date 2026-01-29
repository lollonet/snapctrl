"""API client for Snapcast JSON-RPC over WebSocket."""

from snapctrl.api.client import SnapcastClient
from snapctrl.api.protocol import (
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
