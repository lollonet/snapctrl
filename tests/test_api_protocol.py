"""Tests for JSON-RPC protocol types."""

from snapcast_mvp.api.protocol import (
    JsonRpcError,
    JsonRpcNotification,
    JsonRpcRequest,
    JsonRpcResponse,
)


class TestJsonRpcRequest:
    """Tests for JsonRpcRequest."""

    def test_request_creation(self) -> None:
        """Test creating a request."""
        request = JsonRpcRequest(id=1, method="Server.GetStatus")
        assert request.id == 1
        assert request.method == "Server.GetStatus"
        assert request.params is None

    def test_request_with_params(self) -> None:
        """Test creating a request with parameters."""
        params = {"id": "client-1", "volume": {"percent": 50}}
        request = JsonRpcRequest(id=2, method="Client.SetVolume", params=params)
        assert request.params == params

    def test_to_dict(self) -> None:
        """Test converting request to dict."""
        request = JsonRpcRequest(id=1, method="Server.GetStatus")
        result = request.to_dict()
        assert result == {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "Server.GetStatus",
        }

    def test_to_dict_with_params(self) -> None:
        """Test converting request with params to dict."""
        params = {"volume": 50}
        request = JsonRpcRequest(id=1, method="Client.SetVolume", params=params)
        result = request.to_dict()
        assert result["jsonrpc"] == "2.0"
        assert result["id"] == 1
        assert result["method"] == "Client.SetVolume"
        assert result["params"] == params

    def test_call_factory(self) -> None:
        """Test using the call factory method."""
        request = JsonRpcRequest.call("Server.GetStatus", request_id=5)
        assert request.id == 5
        assert request.method == "Server.GetStatus"
        assert request.params is None

    def test_call_factory_with_params(self) -> None:
        """Test call factory with parameters."""
        params = {"id": "test"}
        request = JsonRpcRequest.call("Method", params, request_id=10)
        assert request.params == params


class TestJsonRpcResponse:
    """Tests for JsonRpcResponse."""

    def test_response_success(self) -> None:
        """Test creating a successful response."""
        response = JsonRpcResponse(id=1, result={"status": "OK"})
        assert response.id == 1
        assert response.result == {"status": "OK"}
        assert response.error is None
        assert response.is_success is True

    def test_response_error(self) -> None:
        """Test creating an error response."""
        error = JsonRpcError(code=-32601, message="Method not found")
        response = JsonRpcResponse(id=1, error=error)
        assert response.error == error
        assert response.is_success is False

    def test_from_dict_success(self) -> None:
        """Test parsing successful response from dict."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"server": {"host": "test"}},
        }
        response = JsonRpcResponse.from_dict(data)
        assert response.id == 1
        assert response.result == {"server": {"host": "test"}}
        assert response.is_success is True

    def test_from_dict_error(self) -> None:
        """Test parsing error response from dict."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {"code": -32601, "message": "Method not found"},
        }
        response = JsonRpcResponse.from_dict(data)
        assert response.is_success is False
        assert response.error is not None
        assert response.error.code == -32601
        assert response.error.message == "Method not found"

    def test_from_dict_error_with_data(self) -> None:
        """Test parsing error response with additional data."""
        data = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -1,
                "message": "Error",
                "data": {"details": "More info"},
            },
        }
        response = JsonRpcResponse.from_dict(data)
        assert response.error is not None
        assert response.error.data == {"details": "More info"}


class TestJsonRpcError:
    """Tests for JsonRpcError."""

    def test_error_creation(self) -> None:
        """Test creating an error."""
        error = JsonRpcError(code=-32700, message="Parse error")
        assert error.code == -32700
        assert error.message == "Parse error"
        assert error.data is None

    def test_error_with_data(self) -> None:
        """Test creating an error with data."""
        error = JsonRpcError(code=-1, message="Custom error", data={"key": "value"})
        assert error.data == {"key": "value"}

    def test_error_str(self) -> None:
        """Test error string representation."""
        error = JsonRpcError(code=-32601, message="Method not found")
        assert str(error) == "[-32601] Method not found"

    def test_error_str_with_data(self) -> None:
        """Test error string representation with data."""
        error = JsonRpcError(code=-1, message="Error", data="details")
        assert "Error" in str(error)
        assert "details" in str(error)


class TestJsonRpcNotification:
    """Tests for JsonRpcNotification."""

    def test_notification_creation(self) -> None:
        """Test creating a notification."""
        notification = JsonRpcNotification(method="OnUpdate", params={"key": "value"})
        assert notification.method == "OnUpdate"
        assert notification.params == {"key": "value"}

    def test_notification_no_params(self) -> None:
        """Test notification without parameters."""
        notification = JsonRpcNotification(method="OnConnect")
        assert notification.method == "OnConnect"
        assert notification.params is None

    def test_from_dict(self) -> None:
        """Test parsing notification from dict."""
        data = {
            "jsonrpc": "2.0",
            "method": "OnUpdate",
            "params": {"clients": ["c1", "c2"]},
        }
        notification = JsonRpcNotification.from_dict(data)
        assert notification.method == "OnUpdate"
        assert notification.params == {"clients": ["c1", "c2"]}

    def test_from_dict_no_params(self) -> None:
        """Test parsing notification without params."""
        data = {"jsonrpc": "2.0", "method": "OnDisconnect"}
        notification = JsonRpcNotification.from_dict(data)
        assert notification.method == "OnDisconnect"
        assert notification.params is None

    def test_from_dict_empty_method(self) -> None:
        """Test parsing notification with empty method."""
        data = {"jsonrpc": "2.0", "method": ""}
        notification = JsonRpcNotification.from_dict(data)
        assert notification.method == ""
