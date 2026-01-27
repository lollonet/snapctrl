"""Main entry point for the Snapcast MVP application."""

import logging
import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from snapcast_mvp.core.discovery import ServerDiscovery
from snapcast_mvp.core.state import StateStore
from snapcast_mvp.core.worker import SnapcastWorker
from snapcast_mvp.ui.main_window import MainWindow

# Enable logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def discover_server() -> tuple[str, int, str] | None:
    """Discover a Snapcast server on the network.

    Returns:
        Tuple of (host, port, hostname) if found, None otherwise.
        hostname is the FQDN from mDNS (e.g., "raspy.local").
    """
    logger.info("Searching for Snapcast servers via mDNS...")
    server = ServerDiscovery.discover_one(timeout=5.0)
    if server:
        logger.info(
            "Found server: %s at %s (%s):%d",
            server.display_name,
            server.hostname or server.host,
            server.host,
            server.port,
        )
        return (server.host, server.port, server.hostname)
    logger.warning("No Snapcast servers found via mDNS")
    return None


def main() -> int:  # noqa: PLR0915
    """Run the Snapcast MVP application.

    Returns:
        Exit code (0 for success).
    """
    app = QApplication(sys.argv)

    # Parse command line arguments
    host: str | None = None
    port = 1705
    hostname: str = ""  # FQDN from mDNS discovery

    args = sys.argv[1:]
    if args:
        host = args[0]
        if len(args) > 1:
            port = int(args[1])
    else:
        # No arguments - try autodiscovery
        result = discover_server()
        if result:
            host, port, hostname = result
        else:
            # Show error dialog and exit
            QMessageBox.critical(
                None,
                "No Server Found",
                "Could not find a Snapcast server on the network.\n\n"
                "Please specify a server address:\n"
                "  snapcast-mvp <host> [port]",
            )
            return 1

    # At this point host is guaranteed to be set (either from args or autodiscovery)
    assert host is not None

    # Create core components
    state_store = StateStore()
    worker = SnapcastWorker(host, port)

    # Connect worker signals to state store
    def on_state_received(state: object) -> None:
        logger.info(f"State received: {state}")
        state_store.update_from_server_state(state)  # type: ignore[arg-type]

    def on_connected() -> None:
        logger.info("Connected to server")

    def on_error(err: object) -> None:
        logger.error(f"Error: {err}")

    worker.state_received.connect(on_state_received)
    worker.connected.connect(on_connected)
    worker.disconnected.connect(state_store.clear)
    worker.connection_lost.connect(state_store.clear)
    worker.error_occurred.connect(on_error)

    # Create main window
    window = MainWindow(state_store=state_store)
    # Show hostname (FQDN) and IP in title if discovered via mDNS
    if hostname:
        window.setWindowTitle(f"Snapcast MVP - {hostname} ({host}):{port}")
    else:
        window.setWindowTitle(f"Snapcast MVP - {host}:{port}")
    window.show()

    # Wire UI signals to worker for volume/mute control
    # Track base volumes for proportional group volume control
    group_base_volumes: dict[str, dict[str, int]] = {}  # group_id -> {client_id -> base_volume}
    group_slider_start: dict[str, int] = {}  # group_id -> slider start value

    def on_client_volume_changed(client_id: str, volume: int) -> None:
        client = state_store.get_client(client_id)
        muted = client.muted if client else False
        logger.debug(f"Client volume: {client_id} -> {volume} (muted={muted})")
        worker.set_client_volume(client_id, volume, muted)

    def on_client_mute_toggled(client_id: str, muted: bool) -> None:
        logger.debug(f"Client mute: {client_id} -> {muted}")
        worker.set_client_mute(client_id, muted)

    def on_group_volume_changed(group_id: str, volume: int) -> None:
        """Scale all clients in group proportionally based on slider movement."""
        group = state_store.get_group(group_id)
        if not group:
            return

        # Initialize base volumes on first interaction
        if group_id not in group_base_volumes:
            group_base_volumes[group_id] = {}
            for client_id in group.client_ids:
                client = state_store.get_client(client_id)
                if client:
                    group_base_volumes[group_id][client_id] = client.volume
            group_slider_start[group_id] = 50  # Default slider position

        start_value = group_slider_start.get(group_id, 50)
        if start_value == 0:
            start_value = 1  # Avoid division by zero

        # Calculate scale factor: slider at 100 = 2x base, slider at 50 = 1x base, slider at 0 = 0x
        scale = volume / start_value

        logger.debug(f"Group volume: {group_id} -> {volume} (scale={scale:.2f})")

        # Calculate new volumes and update both UI and server
        new_volumes: dict[str, int] = {}
        for client_id in group.client_ids:
            base_vol = group_base_volumes[group_id].get(client_id, 50)
            new_vol = min(100, max(0, int(base_vol * scale)))
            new_volumes[client_id] = new_vol
            client = state_store.get_client(client_id)
            muted = client.muted if client else False
            worker.set_client_volume(client_id, new_vol, muted)

        # Update client sliders visually (signals blocked, no cascade)
        window.groups_panel.set_all_client_volumes(group_id, new_volumes)

    def on_group_mute_toggled(group_id: str, muted: bool) -> None:
        logger.debug(f"Group mute: {group_id} -> {muted}")
        worker.set_group_mute(group_id, muted)

    def on_source_changed(group_id: str, stream_id: str) -> None:
        logger.debug(f"Group source: {group_id} -> {stream_id}")
        worker.set_group_stream(group_id, stream_id)

    # Connect GroupsPanel signals
    window.groups_panel.client_volume_changed.connect(on_client_volume_changed)
    window.groups_panel.client_mute_toggled.connect(on_client_mute_toggled)
    window.groups_panel.volume_changed.connect(on_group_volume_changed)
    window.groups_panel.mute_toggled.connect(on_group_mute_toggled)
    window.groups_panel.source_changed.connect(on_source_changed)

    # Start worker thread
    worker.start()

    # Run the application
    exit_code = app.exec()

    # Cleanup
    worker.stop()
    worker.wait()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
