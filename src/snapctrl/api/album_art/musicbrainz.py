"""MusicBrainz Cover Art Archive album art provider.

Uses MusicBrainz to search for releases and Cover Art Archive
to fetch the actual artwork. Free and community-driven.

Adapted from rpi-snapclient-usb metadata-service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from snapctrl.api.album_art.provider import AlbumArt, AlbumArtProvider

logger = logging.getLogger(__name__)

# MusicBrainz API endpoint
MUSICBRAINZ_API_URL = "https://musicbrainz.org/ws/2"

# Cover Art Archive endpoint
COVER_ART_URL = "https://coverartarchive.org"

# User agent (MusicBrainz requires contact info)
USER_AGENT = "SnapCTRL/1.0 (https://github.com/lollonet/snapctrl)"

# Request timeout in seconds
REQUEST_TIMEOUT = 5

# Artwork size suffix
ARTWORK_SIZE = "500"  # front-500 for 500px


class MusicBrainzAlbumArtProvider(AlbumArtProvider):
    """Fetch album art from MusicBrainz/Cover Art Archive.

    Two-step process:
    1. Search MusicBrainz for release MBID
    2. Fetch cover art from Cover Art Archive

    Example:
        provider = MusicBrainzAlbumArtProvider()
        art = await provider.fetch("Fatboy Slim", "That Old Pair of Jeans")
        if art:
            save_image(art.data, "cover.jpg")
    """

    @property
    def name(self) -> str:
        """Return provider name."""
        return "MusicBrainz"

    async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
        """Fetch album art from MusicBrainz/Cover Art Archive.

        Args:
            artist: Artist name (required).
            album: Album name (required for MusicBrainz).
            title: Track title (not used, MusicBrainz needs album).

        Returns:
            AlbumArt if found, None otherwise.
        """
        _ = title  # Not used by MusicBrainz, requires album
        if not artist or not album:
            return None

        # Search MusicBrainz for release
        mbid = await self._search_release(artist, album)
        if not mbid:
            return None

        # Fetch cover art
        artwork_url = f"{COVER_ART_URL}/release/{mbid}/front-{ARTWORK_SIZE}"
        data = await self._download_image(artwork_url)
        if not data:
            return None

        return AlbumArt(
            data=data,
            mime_type="image/jpeg",
            url=artwork_url,
            source=self.name,
        )

    async def _search_release(self, artist: str, album: str) -> str:
        """Search MusicBrainz for release MBID.

        Args:
            artist: Artist name.
            album: Album name.

        Returns:
            Release MBID or empty string if not found.
        """
        try:
            # Build Lucene query for MusicBrainz
            query = urllib.parse.quote(f'artist:"{artist}" AND release:"{album}"')
            url = f"{MUSICBRAINZ_API_URL}/release/?query={query}&fmt=json&limit=1"

            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._fetch_json, url)

            if result:
                releases = result.get("releases", [])
                if releases:
                    mbid = releases[0].get("id")
                    if mbid:
                        logger.debug(
                            "Found MusicBrainz release %s for %s - %s", mbid, artist, album
                        )
                        return mbid

        except Exception as e:  # noqa: BLE001
            logger.debug("MusicBrainz search failed for '%s - %s': %s", artist, album, e)

        return ""

    async def _download_image(self, url: str) -> bytes:
        """Download image from Cover Art Archive.

        Note: Cover Art Archive returns 307 redirects to actual image.
        urllib follows redirects automatically.

        Args:
            url: Image URL.

        Returns:
            Image bytes or empty bytes on failure.
        """
        try:
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._fetch_binary, url)
        except Exception as e:  # noqa: BLE001
            logger.debug("Failed to download image from %s: %s", url, e)
            return b""

    def _fetch_json(self, url: str) -> dict[str, Any] | None:
        """Fetch JSON from URL (blocking).

        Args:
            url: URL to fetch.

        Returns:
            Parsed JSON or None on failure.
        """
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            return json.loads(response.read().decode())

    def _fetch_binary(self, url: str) -> bytes:
        """Fetch binary data from URL (blocking).

        Args:
            url: URL to fetch.

        Returns:
            Binary data.
        """
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as response:
            return response.read()
