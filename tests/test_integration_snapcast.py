"""Integration tests against real Snapcast server.

These tests require network access to a live Snapcast server.
Run with: pytest -v -m integration

Server: raspy (192.168.63.3:1705)
"""

import pytest

from snapcast_mvp.api.client import SnapcastClient
from snapcast_mvp.models import Client, Group, Server, ServerState, Source

# Test server configuration
SNAPCAST_HOST = "192.168.63.3"
SNAPCAST_PORT = 1705


@pytest.mark.integration
class TestSnapcastIntegration:
    """Integration tests against real Snapcast server."""

    @pytest.mark.asyncio
    async def test_connect_to_server(self) -> None:
        """Test that we can connect to the real Snapcast server."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            assert client.is_connected is True

    @pytest.mark.asyncio
    async def test_get_status(self) -> None:
        """Test retrieving server status."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            # Validate ServerState structure
            assert isinstance(state, ServerState)
            assert state.is_connected is True
            assert isinstance(state.server, Server)

            # Server info should be populated
            assert len(state.server.host) > 0

    @pytest.mark.asyncio
    async def test_get_rpc_version(self) -> None:
        """Test getting JSON-RPC version."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            version = await client.get_rpc_version()

            assert isinstance(version, dict)
            assert "major" in version
            assert "minor" in version
            # Snapcast uses JSON-RPC 2.0 (some versions report 23)
            assert version["major"] in (2, 23)

    @pytest.mark.asyncio
    async def test_parse_real_server_data(self) -> None:
        """Test parsing real server response."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            # Validate groups
            assert hasattr(state, "groups")
            assert isinstance(state.groups, list)
            for group in state.groups:
                assert isinstance(group, Group)
                assert len(group.id) > 0
                assert isinstance(group.client_ids, list)

            # Validate clients
            assert hasattr(state, "clients")
            assert isinstance(state.clients, list)
            for client_obj in state.clients:
                assert isinstance(client_obj, Client)
                assert len(client_obj.id) > 0
                assert len(client_obj.host) > 0
                assert 0 <= client_obj.volume <= 100
                assert isinstance(client_obj.connected, bool)

            # Validate sources (streams)
            assert hasattr(state, "sources")
            assert isinstance(state.sources, list)
            for source in state.sources:
                assert isinstance(source, Source)
                assert len(source.id) > 0

    @pytest.mark.asyncio
    async def test_server_version(self) -> None:
        """Test that we get server version info."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            # Version should be populated
            assert len(state.version) > 0
            assert "." in state.version  # Should be like "0.27.0"

    @pytest.mark.asyncio
    async def test_client_lookup(self) -> None:
        """Test client lookup methods work with real data."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            if state.client_count > 0:
                # Test get_client with valid ID
                first_client = state.clients[0]
                found = state.get_client(first_client.id)
                assert found is not None
                assert found.id == first_client.id

                # Test get_client with invalid ID
                not_found = state.get_client("invalid-id-12345")
                assert not_found is None

    @pytest.mark.asyncio
    async def test_group_lookup(self) -> None:
        """Test group lookup methods work with real data."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            if state.group_count > 0:
                # Test get_group with valid ID
                first_group = state.groups[0]
                found = state.get_group(first_group.id)
                assert found is not None
                assert found.id == first_group.id

                # Test get_group with invalid ID
                not_found = state.get_group("invalid-group-12345")
                assert not_found is None

    @pytest.mark.asyncio
    async def test_source_lookup(self) -> None:
        """Test source lookup methods work with real data."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            if state.source_count > 0:
                # Test get_source with valid ID
                first_source = state.sources[0]
                found = state.get_source(first_source.id)
                assert found is not None
                assert found.id == first_source.id

                # Test get_source with invalid ID
                not_found = state.get_source("invalid-source-12345")
                assert not_found is None

    @pytest.mark.asyncio
    async def test_multiple_requests_same_connection(self) -> None:
        """Test multiple requests on the same connection."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            # First request
            state1 = await client.get_status()
            assert state1 is not None

            # Second request on same connection
            state2 = await client.get_status()
            assert state2 is not None

            # Third request - RPC version
            version = await client.get_rpc_version()
            assert version is not None

    @pytest.mark.asyncio
    async def test_reconnection(self) -> None:
        """Test disconnect and reconnect."""
        client = SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT)

        # First connection
        await client.connect()
        assert client.is_connected is True
        state1 = await client.get_status()
        await client.disconnect()

        # Reconnect
        await client.connect()
        assert client.is_connected is True
        state2 = await client.get_status()
        await client.disconnect()

        # Both should return similar data
        assert state1.group_count == state2.group_count
        assert state1.client_count == state2.client_count

    @pytest.mark.asyncio
    async def test_connection_properties(self) -> None:
        """Test client connection properties."""
        client = SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT)
        assert client.host == SNAPCAST_HOST
        assert client.port == SNAPCAST_PORT
        assert client.is_connected is False


@pytest.mark.integration
class TestSnapcastReadOnly:
    """Read-only tests - safe to run on production server."""

    @pytest.mark.asyncio
    async def test_list_all_groups(self) -> None:
        """Test listing all groups from real server."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            print(f"\n=== Groups on {SNAPCAST_HOST} ===")
            for group in state.groups:
                playing = (
                    "▶"
                    if any(s.is_playing for s in state.sources if s.id == group.stream_id)
                    else "⏸"
                )
                print(f"  - {group.name or group.id} ({group.id[:8]}...)")
                print(f"    Stream: {group.stream_id} {playing}")
                print(f"    Muted: {group.muted}")
                print(f"    Clients: {len(group.client_ids)}")

    @pytest.mark.asyncio
    async def test_list_all_clients(self) -> None:
        """Test listing all clients from real server."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            print(f"\n=== Clients on {SNAPCAST_HOST} ===")
            for client_obj in state.clients:
                status = "✓" if client_obj.connected else "✗"
                muted = "🔇" if client_obj.muted else "🔊"
                print(f"  - {client_obj.name or client_obj.id}")
                print(f"    Host: {client_obj.host}")
                print(f"    Status: {status}")
                print(f"    Volume: {client_obj.volume}% {muted}")
                if client_obj.latency > 0:
                    print(f"    Latency: {client_obj.latency}ms")
                print(f"    Version: {client_obj.snapclient_version}")

    @pytest.mark.asyncio
    async def test_list_all_sources(self) -> None:
        """Test listing all sources from real server."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            print(f"\n=== Sources on {SNAPCAST_HOST} ===")
            for source in state.sources:
                playing = "▶" if source.is_playing else "⏸"
                print(f"  - {source.name or source.id}")
                print(f"    Status: {source.status} {playing}")
                print(f"    Type: {source.stream_type}")

    @pytest.mark.asyncio
    async def test_client_to_group_mapping(self) -> None:
        """Test that clients are correctly mapped to groups."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            print("\n=== Client → Group Mapping ===")
            for group in state.groups:
                print(f"\nGroup: {group.name or group.id}")
                for client_id in group.client_ids:
                    client_obj = state.get_client(client_id)
                    if client_obj:
                        print(f"  - {client_obj.name or client_obj.id}: {client_obj.host}")
                    else:
                        print(f"  - {client_id}: [NOT FOUND]")

    @pytest.mark.asyncio
    async def test_source_to_group_mapping(self) -> None:
        """Test that groups are correctly mapped to sources."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            print("\n=== Source → Group Mapping ===")
            for source in state.sources:
                print(f"\nSource: {source.name or source.id}")
                groups_using = [g for g in state.groups if g.stream_id == source.id]
                for group in groups_using:
                    playing = "▶" if source.is_playing else "⏸"
                    print(f"  - {group.name or group.id} {playing}")


@pytest.mark.integration
class TestSnapcastWrite:
    """Tests that modify server state - use with caution!

    These tests will actually change volumes and mute states on your server.
    Skip these with: pytest -v -m integration -k "not TestSnapcastWrite"
    """

    @pytest.mark.asyncio
    async def test_get_client_by_id_for_write(self) -> None:
        """Find a client ID for write tests."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            # Find a connected client for testing
            for client_obj in state.clients:
                if client_obj.connected:
                    print(
                        f"\n=== Found writable client: {client_obj.name} ({client_obj.id[:8]}...)"
                    )
                    print(f"   Current volume: {client_obj.volume}%, muted: {client_obj.muted}")
                    return

            pytest.skip("No connected clients available for write tests")

    @pytest.mark.asyncio
    async def test_toggle_client_mute(self) -> None:
        """Test toggling client mute (will change audio!)."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            # Find a connected client
            test_client = None
            for client_obj in state.clients:
                if client_obj.connected:
                    test_client = client_obj
                    break

            if not test_client:
                pytest.skip("No connected clients available")

            original_muted = test_client.muted

            # Toggle mute
            new_muted = not original_muted
            await client.set_client_volume(
                test_client.id,
                test_client.volume,
                muted=new_muted,
            )

            # Verify change
            state_new = await client.get_status()
            updated_client = state_new.get_client(test_client.id)
            assert updated_client is not None
            assert updated_client.muted == new_muted

            # Toggle back
            await client.set_client_volume(
                test_client.id,
                updated_client.volume,
                muted=original_muted,
            )

    @pytest.mark.asyncio
    async def test_set_group_mute(self) -> None:
        """Test muting/unmuting a group (will change audio!)."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            if state.group_count == 0:
                pytest.skip("No groups available")

            test_group = state.groups[0]

            # Mute the group
            await client.set_group_mute(test_group.id, True)
            state_muted = await client.get_status()
            assert state_muted.get_group(test_group.id).muted is True

            # Unmute
            await client.set_group_mute(test_group.id, False)
            state_unmuted = await client.get_status()
            assert state_unmuted.get_group(test_group.id).muted is False

    @pytest.mark.asyncio
    async def test_volume_change_safe(self) -> None:
        """Test small volume change (will change audio!)."""
        async with SnapcastClient(SNAPCAST_HOST, SNAPCAST_PORT) as client:
            state = await client.get_status()

            # Find a connected client
            test_client = None
            for client_obj in state.clients:
                if client_obj.connected:
                    test_client = client_obj
                    break

            if not test_client:
                pytest.skip("No connected clients available")

            original_volume = test_client.volume
            new_volume = max(0, min(100, original_volume + 5))  # Small change

            # Change volume
            await client.set_client_volume(test_client.id, new_volume)

            # Verify
            state_new = await client.get_status()
            updated_client = state_new.get_client(test_client.id)
            assert updated_client is not None
            assert updated_client.volume == new_volume

            # Restore
            await client.set_client_volume(test_client.id, original_volume)
