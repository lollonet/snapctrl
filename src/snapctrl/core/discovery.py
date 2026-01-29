"""mDNS/Zeroconf discovery for Snapcast servers."""

from __future__ import annotations

import logging
import socket
import threading
from collections.abc import Callable
from dataclasses import dataclass

from zeroconf import ServiceBrowser, ServiceListener, Zeroconf

logger = logging.getLogger(__name__)

# Snapcast mDNS service type (advertised by snapserver)
SNAPCAST_SERVICE_TYPE = "_snapcast._tcp.local."

# The mDNS service advertises the streaming port; the JSON-RPC control port is +1
CONTROL_PORT_OFFSET = 1


@dataclass
class DiscoveredServer:
    """A discovered Snapcast server."""

    name: str
    host: str
    port: int
    addresses: list[str]
    hostname: str = ""  # FQDN from mDNS (e.g., "raspy.local")

    @property
    def display_name(self) -> str:
        """Return a display-friendly name."""
        # Remove .local. suffix if present
        name = self.name
        if name.endswith(f".{SNAPCAST_SERVICE_TYPE}"):
            name = name[: -len(f".{SNAPCAST_SERVICE_TYPE}") - 1]
        return name or self.host


class SnapcastServiceListener(ServiceListener):
    """Listener for Snapcast mDNS service announcements."""

    def __init__(
        self,
        on_found: Callable[[DiscoveredServer], None] | None = None,
        on_removed: Callable[[str], None] | None = None,
    ) -> None:
        """Initialize the listener.

        Args:
            on_found: Callback when a server is discovered.
            on_removed: Callback when a server is removed.
        """
        self._on_found = on_found
        self._on_removed = on_removed
        self._servers: dict[str, DiscoveredServer] = {}

    @property
    def servers(self) -> list[DiscoveredServer]:
        """Return list of discovered servers."""
        return list(self._servers.values())

    def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Handle service discovery."""
        info = zc.get_service_info(type_, name)
        if info is None:
            logger.debug("Could not get info for service: %s", name)
            return

        # Get addresses
        addresses: list[str] = []
        for addr in info.addresses:
            try:
                addresses.append(socket.inet_ntoa(addr))
            except OSError:
                # Try IPv6
                try:
                    addresses.append(socket.inet_ntop(socket.AF_INET6, addr))
                except OSError as e:
                    logger.debug("Could not parse address for %s: %s", name, e)
                    continue

        if not addresses:
            logger.debug("No addresses found for service: %s", name)
            return

        # Prefer server name from properties, fall back to mDNS name
        server_name = ""
        if info.properties:
            name_bytes = info.properties.get(b"name")
            if name_bytes:
                server_name = name_bytes.decode("utf-8", errors="replace")

        # mDNS advertises streaming port, control port is +1
        streaming_port = info.port or 1704
        control_port = streaming_port + CONTROL_PORT_OFFSET

        # Get hostname (FQDN) from mDNS, strip trailing dot
        hostname = info.server.rstrip(".") if info.server else ""

        server = DiscoveredServer(
            name=server_name or name,
            host=addresses[0],  # Use first address
            port=control_port,
            addresses=addresses,
            hostname=hostname,
        )

        logger.info(
            "Discovered Snapcast server: %s at %s:%d", server.name, server.host, server.port
        )
        self._servers[name] = server

        if self._on_found:
            self._on_found(server)

    def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:  # noqa: ARG002
        """Handle service removal."""
        if name in self._servers:
            logger.info("Snapcast server removed: %s", name)
            del self._servers[name]
            if self._on_removed:
                self._on_removed(name)

    def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
        """Handle service update (re-add to refresh info)."""
        self.add_service(zc, type_, name)


class ServerDiscovery:
    """Discovers Snapcast servers on the local network via mDNS.

    Example:
        # Blocking discovery (find first server)
        server = ServerDiscovery.discover_one(timeout=5.0)
        if server:
            print(f"Found: {server.host}:{server.port}")

        # Background discovery with callbacks
        discovery = ServerDiscovery()
        discovery.start(on_found=lambda s: print(f"Found: {s.name}"))
        # ... later ...
        discovery.stop()
    """

    def __init__(self) -> None:
        """Initialize the discovery service."""
        self._zeroconf: Zeroconf | None = None
        self._browser: ServiceBrowser | None = None
        self._listener: SnapcastServiceListener | None = None

    @property
    def servers(self) -> list[DiscoveredServer]:
        """Return list of currently discovered servers."""
        if self._listener:
            return self._listener.servers
        return []

    def start(
        self,
        on_found: Callable[[DiscoveredServer], None] | None = None,
        on_removed: Callable[[str], None] | None = None,
    ) -> None:
        """Start background discovery.

        Args:
            on_found: Callback when a server is discovered.
            on_removed: Callback when a server is removed.
        """
        if self._zeroconf is not None:
            return  # Already running

        self._zeroconf = Zeroconf()
        self._listener = SnapcastServiceListener(on_found=on_found, on_removed=on_removed)
        self._browser = ServiceBrowser(
            self._zeroconf,
            SNAPCAST_SERVICE_TYPE,
            self._listener,
        )
        logger.debug("Started mDNS discovery for Snapcast servers")

    def stop(self) -> None:
        """Stop background discovery."""
        if self._browser:
            self._browser.cancel()
            self._browser = None

        if self._zeroconf:
            self._zeroconf.close()
            self._zeroconf = None

        self._listener = None
        logger.debug("Stopped mDNS discovery")

    @staticmethod
    def discover_one(timeout: float = 5.0) -> DiscoveredServer | None:
        """Discover and return the first Snapcast server found.

        Args:
            timeout: Maximum time to wait in seconds.

        Returns:
            First discovered server, or None if no server found.
        """
        result: DiscoveredServer | None = None
        found_event = threading.Event()

        def on_found(server: DiscoveredServer) -> None:
            nonlocal result
            if result is None:
                result = server
                found_event.set()

        discovery = ServerDiscovery()
        discovery.start(on_found=on_found)

        try:
            found_event.wait(timeout=timeout)
        finally:
            discovery.stop()

        return result

    @staticmethod
    def discover_all(timeout: float = 5.0) -> list[DiscoveredServer]:
        """Discover all Snapcast servers within timeout.

        Args:
            timeout: Time to wait for discovery in seconds.

        Returns:
            List of discovered servers.
        """
        discovery = ServerDiscovery()
        discovery.start()

        try:
            # Wait for the timeout period to collect all servers
            threading.Event().wait(timeout=timeout)
        finally:
            servers = discovery.servers.copy()
            discovery.stop()

        return servers
