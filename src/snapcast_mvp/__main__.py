"""Main entry point for the SnapCTRL application."""

import base64
import logging
import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from snapcast_mvp.api.mpd import MpdTrack
from snapcast_mvp.api.protocol import JsonRpcNotification
from snapcast_mvp.core.discovery import ServerDiscovery
from snapcast_mvp.core.mpd_monitor import MpdMonitor
from snapcast_mvp.core.ping import PingMonitor
from snapcast_mvp.core.state import StateStore
from snapcast_mvp.core.worker import SnapcastWorker
from snapcast_mvp.models.source import Source
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
    """Run the SnapCTRL application.

    Returns:
        Exit code (0 for success).
    """
    # Set app metadata before creating QApplication (required for macOS)
    QApplication.setApplicationName("SnapCTRL")
    QApplication.setApplicationDisplayName("SnapCTRL")
    QApplication.setOrganizationName("SnapCTRL")
    QApplication.setOrganizationDomain("snapctrl.local")

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

        # Reset base volumes for groups whose slider hasn't been used recently
        # This allows external changes (from mobile app) to update the group slider
        current_time = time.time()
        stale_threshold = 1.0  # seconds - reset if slider inactive for this long

        for group_id in list(group_base_volumes.keys()):
            last_active = group_slider_active.get(group_id, 0)
            if current_time - last_active > stale_threshold:
                # Slider is stale, reset base volumes to allow external updates
                del group_base_volumes[group_id]
                if group_id in group_slider_start:
                    del group_slider_start[group_id]

    def on_connected() -> None:
        logger.info("Connected to server")

    def on_error(err: object) -> None:
        logger.error(f"Error: {err}")

    # Debounce timer for notifications to avoid UI flickering during volume changes
    notification_timer: QTimer | None = None
    pending_refresh = False

    def do_refresh() -> None:
        nonlocal pending_refresh
        if pending_refresh:
            pending_refresh = False
            worker.request_status()

    def on_notification(notification: object) -> None:
        """Handle server notification by refreshing state with debounce."""
        nonlocal notification_timer, pending_refresh

        if isinstance(notification, JsonRpcNotification):
            logger.debug(f"Server notification: {notification.method}")

            # Skip volume notifications if we recently changed volume (avoid feedback loop)
            if notification.method == "Client.OnVolumeChanged":
                # Mark that we need a refresh but debounce it
                pending_refresh = True
                if notification_timer is None:
                    notification_timer = QTimer()
                    notification_timer.setSingleShot(True)
                    notification_timer.timeout.connect(do_refresh)
                # Reset timer - only refresh 300ms after last notification
                notification_timer.start(300)
            else:
                # Other notifications (connect, disconnect, etc.) refresh immediately
                worker.request_status()

    worker.state_received.connect(on_state_received)
    worker.connected.connect(on_connected)
    worker.disconnected.connect(state_store.clear)
    worker.connection_lost.connect(state_store.clear)
    worker.error_occurred.connect(on_error)
    worker.notification_received.connect(on_notification)

    # Create main window
    window = MainWindow(state_store=state_store)
    # Show hostname (FQDN) and IP in title if discovered via mDNS
    if hostname:
        window.setWindowTitle(f"SnapCTRL - {hostname} ({host}):{port}")
    else:
        window.setWindowTitle(f"SnapCTRL - {host}:{port}")

    # Set app icon
    icon_path = Path(__file__).parent.parent.parent / "resources" / "icon.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        window.setWindowIcon(QIcon(str(icon_path)))

    window.show()

    # Wire UI signals to worker for volume/mute control
    # Track base volumes for proportional group volume control
    group_base_volumes: dict[str, dict[str, int]] = {}  # group_id -> {client_id -> base_volume}
    group_slider_start: dict[str, int] = {}  # group_id -> slider start value
    group_slider_active: dict[str, float] = {}  # group_id -> timestamp when slider was last used

    def on_client_volume_changed(client_id: str, volume: int) -> None:
        client = state_store.get_client(client_id)
        muted = client.muted if client else False
        # Auto-mute at volume 0 to ensure true silence on all clients
        if volume == 0:
            muted = True
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

        # Mark this group's slider as active
        group_slider_active[group_id] = time.time()

        # Initialize base volumes on first interaction or after reset
        if group_id not in group_base_volumes:
            group_base_volumes[group_id] = {}
            for client_id in group.client_ids:
                client = state_store.get_client(client_id)
                if client:
                    group_base_volumes[group_id][client_id] = client.volume
            # Calculate average volume as slider start position
            volumes = list(group_base_volumes[group_id].values())
            group_slider_start[group_id] = sum(volumes) // len(volumes) if volumes else 50

        start_value = group_slider_start.get(group_id, 50)
        if start_value == 0:
            start_value = 1  # Avoid division by zero

        # Calculate scale factor based on slider movement from start position
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
            # Auto-mute at volume 0 to ensure true silence on all clients
            if new_vol == 0:
                muted = True
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

    # Set up ping monitor for network RTT measurement
    ping_monitor = PingMonitor(interval_sec=15.0)

    def update_ping_hosts() -> None:
        """Update ping monitor with current client IPs."""
        hosts = {c.id: c.host for c in state_store.clients if c.host}
        ping_monitor.set_hosts(hosts)

    def on_ping_results(results: dict[str, float | None]) -> None:
        """Handle ping results update."""
        logger.debug(f"Ping results: {results}")
        # Store results in window for PropertiesPanel access
        window.set_ping_results(results)

    ping_monitor.results_updated.connect(on_ping_results)

    # Update ping hosts when state changes
    def on_clients_changed_for_ping(_clients: list[object]) -> None:
        update_ping_hosts()

    state_store.clients_changed.connect(on_clients_changed_for_ping)

    # Start ping monitor
    ping_monitor.start()

    # Set up MPD monitor for track metadata
    # MPD typically runs on the same host as Snapcast server
    mpd_monitor = MpdMonitor(host=host, port=6600)

    def find_mpd_source() -> Source | None:
        """Find the MPD source by name or scheme."""
        mpd_source = state_store.find_source_by_name("MPD")
        if not mpd_source:
            mpd_source = state_store.find_source_by_scheme("pipe")
        return mpd_source

    def on_mpd_track_changed(track: MpdTrack | None) -> None:
        """Handle MPD track change by updating the MPD source metadata."""
        mpd_source = find_mpd_source()
        if not mpd_source:
            return

        if track and track.has_metadata:
            logger.debug(f"MPD track: {track.title} - {track.artist}")
            state_store.update_source_metadata(
                mpd_source.id,
                meta_title=track.display_title,
                meta_artist=track.display_artist,
                meta_album=track.album,
            )
        else:
            # Clear metadata when stopped
            state_store.update_source_metadata(
                mpd_source.id,
                meta_title="",
                meta_artist="",
                meta_album="",
            )

    def on_mpd_art_changed(uri: str, data: bytes, mime_type: str) -> None:
        """Handle album art from MPD."""
        if not data:
            return

        mpd_source = find_mpd_source()
        if not mpd_source:
            return

        # Convert to data URI for display
        if mime_type:
            data_uri = f"data:{mime_type};base64,{base64.b64encode(data).decode()}"
        else:
            # Guess JPEG if no mime type
            data_uri = f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"

        logger.debug(f"MPD album art: {len(data)} bytes for {uri}")

        # Update source metadata with art URL
        state_store.update_source_metadata(
            mpd_source.id,
            meta_title=mpd_source.meta_title,
            meta_artist=mpd_source.meta_artist,
            meta_album=mpd_source.meta_album,
            meta_art_url=data_uri,
        )

    def on_mpd_error(error: str) -> None:
        """Handle MPD connection errors."""
        logger.warning(f"MPD error: {error}")

    mpd_monitor.track_changed.connect(on_mpd_track_changed)
    mpd_monitor.art_changed.connect(on_mpd_art_changed)
    mpd_monitor.error_occurred.connect(on_mpd_error)

    # Start MPD monitor
    mpd_monitor.start()

    # Start worker thread
    worker.start()

    # Run the application
    exit_code = app.exec()

    # Cleanup
    mpd_monitor.stop()
    ping_monitor.stop()
    worker.stop()
    worker.wait()

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
