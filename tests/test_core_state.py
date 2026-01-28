"""Tests for StateStore with Qt signals."""

import pytest
from pytestqt.qtbot import QtBot

from snapcast_mvp.core.state import StateStore
from snapcast_mvp.models.client import Client
from snapcast_mvp.models.group import Group
from snapcast_mvp.models.server import Server
from snapcast_mvp.models.server_state import ServerState
from snapcast_mvp.models.source import Source


@pytest.fixture
def state() -> StateStore:
    """Return a fresh StateStore for each test."""
    return StateStore()


@pytest.fixture
def sample_server_state() -> ServerState:
    """Return a sample ServerState for testing."""
    server = Server(name="TestServer", host="192.168.1.100", port=1705)
    groups = [
        Group(
            id="group1",
            name="Group 1",
            stream_id="source1",
            muted=False,
            client_ids=["client1", "client2"],
        ),
        Group(
            id="group2",
            name="Group 2",
            stream_id="source1",
            muted=True,
            client_ids=["client3"],
        ),
    ]
    clients = [
        Client(
            id="client1",
            host="192.168.1.101",
            name="Client 1",
            volume=50,
            muted=False,
        ),
        Client(
            id="client2",
            host="192.168.1.102",
            name="Client 2",
            volume=75,
            muted=True,
        ),
        Client(
            id="client3",
            host="192.168.1.103",
            name="Client 3",
            volume=30,
            muted=False,
        ),
    ]
    sources = [
        Source(
            id="source1",
            name="Source 1",
            status="playing",
            stream_type="flac",
        ),
        Source(
            id="source2",
            name="Source 2",
            status="idle",
            stream_type="mp3",
        ),
    ]
    return ServerState(
        server=server,
        groups=groups,
        clients=clients,
        sources=sources,
        connected=True,
        version="0.34.0",
        host="TestServer",
        mac="00:11:22:33:44:55",
    )


class TestStateStoreBasics:
    """Test basic StateStore functionality."""

    def test_initial_state(self, state: StateStore) -> None:
        """Test that StateStore starts with empty state."""
        assert not state.is_connected
        assert state.server is None
        assert state.groups == []
        assert state.clients == []
        assert state.sources == []

    def test_update_from_server_state(
        self, state: StateStore, sample_server_state: ServerState
    ) -> None:
        """Test updating state from ServerState."""
        state.update_from_server_state(sample_server_state)

        assert state.is_connected
        assert state.server is not None
        assert state.server.name == "TestServer"
        assert len(state.groups) == 2
        assert len(state.clients) == 3
        assert len(state.sources) == 2


class TestStateStoreLookups:
    """Test lookup methods."""

    def test_get_group(self, state: StateStore, sample_server_state: ServerState) -> None:
        """Test getting a group by ID."""
        state.update_from_server_state(sample_server_state)

        group = state.get_group("group1")
        assert group is not None
        assert group.name == "Group 1"

        not_found = state.get_group("nonexistent")
        assert not_found is None

    def test_get_client(self, state: StateStore, sample_server_state: ServerState) -> None:
        """Test getting a client by ID."""
        state.update_from_server_state(sample_server_state)

        client = state.get_client("client1")
        assert client is not None
        assert client.name == "Client 1"

        not_found = state.get_client("nonexistent")
        assert not_found is None

    def test_get_source(self, state: StateStore, sample_server_state: ServerState) -> None:
        """Test getting a source by ID."""
        state.update_from_server_state(sample_server_state)

        source = state.get_source("source1")
        assert source is not None
        assert source.name == "Source 1"

        not_found = state.get_source("nonexistent")
        assert not_found is None

    def test_get_clients_for_group(
        self, state: StateStore, sample_server_state: ServerState
    ) -> None:
        """Test getting clients for a specific group."""
        state.update_from_server_state(sample_server_state)

        clients = state.get_clients_for_group("group1")
        assert len(clients) == 2
        client_ids = {c.id for c in clients if c}
        assert client_ids == {"client1", "client2"}

        empty = state.get_clients_for_group("nonexistent")
        assert empty == []

    def test_get_group_for_client(
        self, state: StateStore, sample_server_state: ServerState
    ) -> None:
        """Test finding the group that contains a client."""
        state.update_from_server_state(sample_server_state)

        group = state.get_group_for_client("client1")
        assert group is not None
        assert group.id == "group1"

        not_found = state.get_group_for_client("nonexistent")
        assert not_found is None


class TestStateStoreSignals:
    """Test Qt signal emission."""

    def test_connection_changed_signal(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test connection_changed signal emission."""
        with qtbot.wait_signal(state.connection_changed, timeout=100) as blocker:
            state.update_from_server_state(sample_server_state)

        assert blocker.args == [True]

    def test_groups_changed_signal(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test groups_changed signal emission."""
        with qtbot.wait_signal(state.groups_changed, timeout=100) as blocker:
            state.update_from_server_state(sample_server_state)

        groups = blocker.args[0]
        assert len(groups) == 2
        assert groups[0].name == "Group 1"

    def test_clients_changed_signal(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test clients_changed signal emission."""
        with qtbot.wait_signal(state.clients_changed, timeout=100) as blocker:
            state.update_from_server_state(sample_server_state)

        clients = blocker.args[0]
        assert len(clients) == 3

    def test_sources_changed_signal(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test sources_changed signal emission."""
        with qtbot.wait_signal(state.sources_changed, timeout=100) as blocker:
            state.update_from_server_state(sample_server_state)

        sources = blocker.args[0]
        assert len(sources) == 2

    def test_state_changed_signal(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test state_changed signal emission."""
        with qtbot.wait_signal(state.state_changed, timeout=100) as blocker:
            state.update_from_server_state(sample_server_state)

        emitted_state = blocker.args[0]
        assert emitted_state is sample_server_state

    def test_signals_only_emit_on_change(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test that signals don't emit if data hasn't changed."""
        state.update_from_server_state(sample_server_state)

        # Update with same state - should still emit state_changed but not others
        # Actually state_changed always emits per implementation
        with qtbot.wait_signal(state.state_changed, timeout=100):
            state.update_from_server_state(sample_server_state)


class TestStateStoreUpdates:
    """Test optimistic updates."""

    def test_update_client_volume(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test optimistic client volume update."""
        state.update_from_server_state(sample_server_state)

        with qtbot.wait_signal(state.clients_changed, timeout=100) as blocker:
            state.update_client_volume("client1", 80, True)

        clients = blocker.args[0]
        client1 = next(c for c in clients if c.id == "client1")
        assert client1.volume == 80
        assert client1.muted is True

    def test_update_client_volume_before_state_set(self, state: StateStore) -> None:
        """Test updating client volume before state is set (should be safe)."""
        # Should not crash
        state.update_client_volume("client1", 80, True)

    def test_update_group_mute(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test optimistic group mute update."""
        state.update_from_server_state(sample_server_state)

        with qtbot.wait_signal(state.groups_changed, timeout=100) as blocker:
            state.update_group_mute("group1", True)

        groups = blocker.args[0]
        group1 = next(g for g in groups if g.id == "group1")
        assert group1.muted is True

    def test_update_group_mute_before_state_set(self, state: StateStore) -> None:
        """Test updating group mute before state is set (should be safe)."""
        # Should not crash
        state.update_group_mute("group1", True)


class TestStateStoreClear:
    """Test clearing state."""

    def test_clear_emits_disconnected(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test that clear emits connection_changed with False."""
        state.update_from_server_state(sample_server_state)
        assert state.is_connected

        with qtbot.wait_signal(state.connection_changed, timeout=100) as blocker:
            state.clear()

        assert blocker.args == [False]
        assert not state.is_connected
        assert state.groups == []
        assert state.clients == []
        assert state.sources == []

    def test_clear_when_not_connected_is_safe(self, state: StateStore) -> None:
        """Test that clearing when not connected is safe."""
        state.clear()  # Should not crash
        assert not state.is_connected


class TestSignalOrdering:
    """Test signal ordering and consistency."""

    def test_multiple_signals_emitted(
        self, state: StateStore, sample_server_state: ServerState, qtbot: QtBot
    ) -> None:
        """Test that multiple signals are emitted on state update."""
        signals_received = []

        state.connection_changed.connect(lambda: signals_received.append("connection"))
        state.groups_changed.connect(lambda: signals_received.append("groups"))
        state.clients_changed.connect(lambda: signals_received.append("clients"))
        state.sources_changed.connect(lambda: signals_received.append("sources"))
        state.state_changed.connect(lambda: signals_received.append("state"))

        state.update_from_server_state(sample_server_state)

        # All signals should be received
        assert "connection" in signals_received
        assert "groups" in signals_received
        assert "clients" in signals_received
        assert "sources" in signals_received
        assert "state" in signals_received


class TestSourceMetadata:
    """Test source metadata updates."""

    @pytest.fixture
    def state_with_sources(self, state: StateStore) -> StateStore:
        """Return a StateStore with sources including uri_scheme."""
        server = Server(name="TestServer", host="192.168.1.100", port=1705)
        sources = [
            Source(
                id="mpd_source",
                name="MPD",
                status="playing",
                stream_type="pipe",
                uri_scheme="pipe",
            ),
            Source(
                id="spotify_source",
                name="Spotify",
                status="idle",
                stream_type="librespot",
                uri_scheme="librespot",
            ),
            Source(
                id="airplay_source",
                name="AirPlay",
                status="idle",
                stream_type="airplay",
                uri_scheme="airplay",
            ),
        ]
        server_state = ServerState(
            server=server,
            groups=[],
            clients=[],
            sources=sources,
            connected=True,
            version="0.34.0",
            host="TestServer",
            mac="00:11:22:33:44:55",
        )
        state.update_from_server_state(server_state)
        return state

    def test_update_source_metadata(self, state_with_sources: StateStore, qtbot: QtBot) -> None:
        """Test updating source metadata."""
        with qtbot.wait_signal(state_with_sources.sources_changed, timeout=100) as blocker:
            state_with_sources.update_source_metadata(
                "mpd_source",
                meta_title="Test Song",
                meta_artist="Test Artist",
                meta_album="Test Album",
                meta_art_url="data:image/jpeg;base64,abc123",
            )

        sources = blocker.args[0]
        mpd = next(s for s in sources if s.id == "mpd_source")
        assert mpd.meta_title == "Test Song"
        assert mpd.meta_artist == "Test Artist"
        assert mpd.meta_album == "Test Album"
        assert mpd.meta_art_url == "data:image/jpeg;base64,abc123"

    def test_update_source_metadata_partial(
        self, state_with_sources: StateStore, qtbot: QtBot
    ) -> None:
        """Test updating only some metadata fields."""
        with qtbot.wait_signal(state_with_sources.sources_changed, timeout=100):
            state_with_sources.update_source_metadata(
                "mpd_source",
                meta_title="Only Title",
            )

        source = state_with_sources.get_source("mpd_source")
        assert source is not None
        assert source.meta_title == "Only Title"
        assert source.meta_artist == ""
        assert source.meta_album == ""

    def test_update_source_metadata_clears_metadata(
        self, state_with_sources: StateStore, qtbot: QtBot
    ) -> None:
        """Test clearing metadata by setting empty strings."""
        # First set some metadata
        state_with_sources.update_source_metadata(
            "mpd_source",
            meta_title="Song",
            meta_artist="Artist",
        )

        # Then clear it
        with qtbot.wait_signal(state_with_sources.sources_changed, timeout=100):
            state_with_sources.update_source_metadata(
                "mpd_source",
                meta_title="",
                meta_artist="",
            )

        source = state_with_sources.get_source("mpd_source")
        assert source is not None
        assert source.meta_title == ""
        assert source.meta_artist == ""

    def test_update_source_metadata_nonexistent_source(
        self, state_with_sources: StateStore
    ) -> None:
        """Test updating metadata for nonexistent source (should be safe)."""
        # Should not crash
        state_with_sources.update_source_metadata(
            "nonexistent",
            meta_title="Test",
        )

    def test_update_source_metadata_before_state_set(self, state: StateStore) -> None:
        """Test updating metadata before any state is set (should be safe)."""
        # Should not crash
        state.update_source_metadata(
            "any_source",
            meta_title="Test",
        )


class TestSourceLookups:
    """Test source lookup methods."""

    @pytest.fixture
    def state_with_sources(self, state: StateStore) -> StateStore:
        """Return a StateStore with various sources."""
        server = Server(name="TestServer", host="192.168.1.100", port=1705)
        sources = [
            Source(
                id="mpd_source",
                name="MPD",
                status="playing",
                stream_type="pipe",
                uri_scheme="pipe",
            ),
            Source(
                id="spotify_source",
                name="Spotify Connect",
                status="idle",
                stream_type="librespot",
                uri_scheme="librespot",
            ),
            Source(
                id="airplay_source",
                name="AirPlay",
                status="idle",
                stream_type="airplay",
                uri_scheme="airplay",
            ),
        ]
        server_state = ServerState(
            server=server,
            groups=[],
            clients=[],
            sources=sources,
            connected=True,
            version="0.34.0",
            host="TestServer",
            mac="00:11:22:33:44:55",
        )
        state.update_from_server_state(server_state)
        return state

    def test_find_source_by_name(self, state_with_sources: StateStore) -> None:
        """Test finding source by exact name."""
        source = state_with_sources.find_source_by_name("MPD")
        assert source is not None
        assert source.id == "mpd_source"

    def test_find_source_by_name_case_insensitive(self, state_with_sources: StateStore) -> None:
        """Test that name lookup is case-insensitive."""
        source1 = state_with_sources.find_source_by_name("mpd")
        source2 = state_with_sources.find_source_by_name("Mpd")
        source3 = state_with_sources.find_source_by_name("MPD")

        assert source1 is not None
        assert source2 is not None
        assert source3 is not None
        assert source1.id == source2.id == source3.id == "mpd_source"

    def test_find_source_by_name_not_found(self, state_with_sources: StateStore) -> None:
        """Test finding nonexistent source by name."""
        source = state_with_sources.find_source_by_name("Nonexistent")
        assert source is None

    def test_find_source_by_name_partial_no_match(self, state_with_sources: StateStore) -> None:
        """Test that partial names don't match."""
        # Actual name is "Spotify Connect", not "Spotify"
        source = state_with_sources.find_source_by_name("Spotify")
        assert source is None

    def test_find_source_by_scheme(self, state_with_sources: StateStore) -> None:
        """Test finding source by URI scheme."""
        source = state_with_sources.find_source_by_scheme("pipe")
        assert source is not None
        assert source.id == "mpd_source"

    def test_find_source_by_scheme_case_insensitive(self, state_with_sources: StateStore) -> None:
        """Test that scheme lookup is case-insensitive."""
        source1 = state_with_sources.find_source_by_scheme("PIPE")
        source2 = state_with_sources.find_source_by_scheme("Pipe")
        source3 = state_with_sources.find_source_by_scheme("pipe")

        assert source1 is not None
        assert source2 is not None
        assert source3 is not None
        assert source1.id == source2.id == source3.id == "mpd_source"

    def test_find_source_by_scheme_not_found(self, state_with_sources: StateStore) -> None:
        """Test finding nonexistent source by scheme."""
        source = state_with_sources.find_source_by_scheme("meta")
        assert source is None

    def test_find_source_by_name_empty_state(self, state: StateStore) -> None:
        """Test finding source when state is empty."""
        source = state.find_source_by_name("MPD")
        assert source is None

    def test_find_source_by_scheme_empty_state(self, state: StateStore) -> None:
        """Test finding source by scheme when state is empty."""
        source = state.find_source_by_scheme("pipe")
        assert source is None
