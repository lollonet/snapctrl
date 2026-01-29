"""Base album art provider and fallback chain.

Defines the provider protocol and a fallback chain that tries
multiple providers in order until one succeeds.
"""

from __future__ import annotations

import logging
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AlbumArt:
    """Album art data from any provider.

    Attributes:
        data: Raw image bytes.
        mime_type: MIME type (e.g., "image/jpeg").
        url: Original URL if fetched from HTTP.
        source: Provider name that supplied this art.
    """

    data: bytes
    mime_type: str = "image/jpeg"
    url: str = ""
    source: str = ""

    @property
    def is_valid(self) -> bool:
        """Check if this album art has valid data."""
        return len(self.data) > 0


class AlbumArtProvider(ABC):
    """Abstract base class for album art providers.

    Subclasses implement fetching album art from a specific source
    (iTunes, MusicBrainz, etc.).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name for logging."""

    @abstractmethod
    async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
        """Fetch album art for the given track.

        Args:
            artist: Artist name.
            album: Album name.
            title: Track title (optional, for single searches).

        Returns:
            AlbumArt if found, None otherwise.
        """


class FallbackAlbumArtProvider(AlbumArtProvider):
    """Album art provider that tries multiple providers in order.

    Stops at the first provider that returns valid art.

    Example:
        provider = FallbackAlbumArtProvider([
            ITunesAlbumArtProvider(),
            MusicBrainzAlbumArtProvider(),
        ])
        art = await provider.fetch("Fatboy Slim", "That Old Pair of Jeans")
    """

    def __init__(self, providers: list[AlbumArtProvider]) -> None:
        """Initialize with a list of providers to try.

        Args:
            providers: Providers to try in order.
        """
        self._providers = providers

    @property
    def name(self) -> str:
        """Return combined provider names."""
        names = [p.name for p in self._providers]
        return f"Fallback({', '.join(names)})"

    async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
        """Try each provider until one succeeds.

        Args:
            artist: Artist name.
            album: Album name.
            title: Track title (optional).

        Returns:
            AlbumArt from first successful provider, None if all fail.
        """
        if not artist:
            return None

        for provider in self._providers:
            try:
                art = await provider.fetch(artist, album, title)
                if art and art.is_valid:
                    logger.debug(
                        "Album art found via %s for %s - %s",
                        provider.name,
                        artist,
                        album or title,
                    )
                    return art
            except (urllib.error.URLError, TimeoutError, OSError) as e:
                # Network errors are expected when providers are unavailable
                logger.debug("%s network error for %s - %s: %s", provider.name, artist, album, e)
            except Exception as e:  # noqa: BLE001
                # Unexpected errors should be logged at warning level
                logger.warning(
                    "%s unexpected error for %s - %s: %s", provider.name, artist, album, e
                )

        logger.debug("No album art found for %s - %s", artist, album or title)
        return None
