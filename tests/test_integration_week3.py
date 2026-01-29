"""Integration test: connect -> state -> signal.

Tests the full Week 3 flow:
1. SnapcastWorker connects to real server
2. StateStore receives state updates
3. Qt signals are emitted
"""

import os

import pytest
from pytestqt.qtbot import QtBot

from snapctrl.core.state import StateStore
from snapctrl.core.worker import SnapcastWorker

# Real server from integration tests
SNAPCAST_HOST = os.getenv("SNAPCAST_HOST", "192.168.63.3")
SNAPCAST_PORT = int(os.getenv("SNAPCAST_PORT", "1705"))


@pytest.mark.integration
def test_worker_connects_and_emits_state(qtbot: QtBot) -> None:
    """Test that worker connects to real server and emits state."""
    worker = SnapcastWorker(SNAPCAST_HOST, SNAPCAST_PORT, timeout=5.0)

    state_received = []
    errors_received = []

    def on_state(state) -> None:
        state_received.append(state)

    def on_error(e) -> None:
        errors_received.append(e)
        print(f"Worker error: {e}")

    worker.state_received.connect(on_state)
    worker.error_occurred.connect(on_error)

    worker.start()

    try:
        # Process events for a bit
        qtbot.wait(200)

        # Check for errors
        if errors_received:
            pytest.fail(f"Connection error: {errors_received[0]}")

        # Wait for connection signal
        if not qtbot.wait_signal(worker.connected, timeout=10000):
            # Check if we're connected anyway
            if worker.is_connected:
                print("Worker is connected but no signal emitted")
            else:
                pytest.fail("Worker did not connect within timeout")

        # Wait for state signal
        if not qtbot.wait_signal(worker.state_received, timeout=5000):
            pytest.fail("Worker did not emit state signal")

        assert len(state_received) > 0, "No state received"
        state = state_received[0]

        # Validate server info
        assert state.server is not None
        assert len(state.groups) > 0, "No groups found"
        assert len(state.clients) > 0, "No clients found"
        assert len(state.sources) > 0, "No sources found"

    finally:
        worker.stop()
        qtbot.wait(500)


@pytest.mark.integration
def test_state_store_receives_updates(qtbot: QtBot) -> None:
    """Test StateStore receives and emits updates from worker."""
    worker = SnapcastWorker(SNAPCAST_HOST, SNAPCAST_PORT, timeout=5.0)
    store = StateStore()

    state_updates = []
    errors_received = []

    def on_state(state) -> None:
        state_updates.append(state)
        store.update_from_server_state(state)

    def on_error(e) -> None:
        errors_received.append(e)

    worker.state_received.connect(on_state)
    worker.error_occurred.connect(on_error)

    worker.start()

    try:
        qtbot.wait(200)

        if errors_received:
            pytest.fail(f"Connection error: {errors_received[0]}")

        # Wait for connection and state
        qtbot.wait_signal(worker.connected, timeout=10000)
        qtbot.wait_signal(store.state_changed, timeout=5000)

        assert len(state_updates) > 0
        assert len(store.groups) > 0
        assert len(store.clients) > 0
        assert len(store.sources) > 0

        # Test lookup methods
        group = store.groups[0]
        assert store.get_group(group.id) is not None

        clients_in_group = store.get_clients_for_group(group.id)
        assert len(clients_in_group) > 0

        for client in clients_in_group:
            if client:
                assert store.get_client(client.id) is not None
                found_group = store.get_group_for_client(client.id)
                assert found_group is not None
                assert found_group.id == group.id

    finally:
        worker.stop()
        qtbot.wait(500)
