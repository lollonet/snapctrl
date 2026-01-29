"""JSON-RPC protocol types for Snapcast communication."""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JsonRpcRequest:
    """A JSON-RPC 2.0 request.

    Attributes:
        id: Request identifier (int or str).
        method: Method name to call.
        params: Method parameters (dict or list).
    """

    id: int | str
    method: str
    params: dict[str, Any] | list[Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        result: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.id,
            "method": self.method,
        }
        if self.params is not None:
            result["params"] = self.params
        return result

    @classmethod
    def call(
        cls,
        method: str,
        params: dict[str, Any] | list[Any] | None = None,
        request_id: int = 1,
    ) -> "JsonRpcRequest":
        """Create a method call request."""
        return cls(id=request_id, method=method, params=params)


@dataclass(frozen=True)
class JsonRpcResponse:
    """A JSON-RPC 2.0 response.

    Attributes:
        id: Request identifier matching the request.
        result: Result data (None if error).
        error: Error data (None if success).
    """

    id: int | str | None = None
    result: Any = None
    error: "JsonRpcError | None" = None

    @property
    def is_success(self) -> bool:
        """Return True if response indicates success."""
        return self.error is None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcResponse":
        """Create response from JSON dict."""
        error_data = data.get("error")
        error: JsonRpcError | None = None
        if error_data is not None:
            error = JsonRpcError(
                code=error_data.get("code", -1),
                message=error_data.get("message", "Unknown error"),
                data=error_data.get("data"),
            )
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=error,
        )


@dataclass(frozen=True)
class JsonRpcError:
    """A JSON-RPC 2.0 error.

    Attributes:
        code: Error code.
        message: Error message.
        data: Additional error data.
    """

    code: int
    message: str
    data: Any = None

    def __str__(self) -> str:
        """Return error message representation."""
        if self.data:
            return f"[{self.code}] {self.message}: {self.data}"
        return f"[{self.code}] {self.message}"


@dataclass(frozen=True)
class JsonRpcNotification:
    """A JSON-RPC 2.0 notification (server-initiated message).

    Attributes:
        method: Notification method name.
        params: Notification parameters.
    """

    method: str
    params: dict[str, Any] | list[Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "JsonRpcNotification":
        """Create notification from JSON dict."""
        return cls(
            method=data.get("method", ""),
            params=data.get("params"),
        )
