"""iTunes Search API album art provider.

Uses Apple's free iTunes Search API to find album artwork.
No authentication required, good coverage for popular music.

Adapted from rpi-snapclient-usb metadata-service.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.parse
import urllib.request
from typing import Any

from snapcast_mvp.api.album_art.provider import AlbumArt, AlbumArtProvider

logger = logging.getLogger(__name__)

# iTunes API endpoint
ITUNES_SEARCH_URL = "https://itunes.apple.com/search"

# User agent for API requests
USER_AGENT = "SnapCTRL/1.0 (https://github.com/lollonet/snapcast-mvp)"

# Request timeout in seconds
REQUEST_TIMEOUT = 5

# Artwork size (replace 100x100 with this)
ARTWORK_SIZE = "600x600"


class ITunesAlbumArtProvider(AlbumArtProvider):
    """Fetch album art from iTunes Search API.

    Example:
        provider = ITunesAlbumArtProvider()
        art = await provider.fetch("Fatboy Slim", "That Old Pair of Jeans")
        if art:
            save_image(art.data, "cover.jpg")
    """

    @property
    def name(self) -> str:
        """Return provider name."""
        return "iTunes"

    async def fetch(self, artist: str, album: str, title: str = "") -> AlbumArt | None:
        """Fetch album art from iTunes.

        Args:
            artist: Artist name (required).
            album: Album name (preferred for search).
            title: Track title (used if no album).

        Returns:
            AlbumArt if found, None otherwise.
        """
        if not artist:
            return None

        # Build search query
        search_term = album if album else title
        if not search_term:
            return None

        query = f"{artist} {search_term}"

        # Search iTunes
        artwork_url = await self._search_itunes(query)
        if not artwork_url:
            return None

        # Download the artwork
        data = await self._download_image(artwork_url)
        if not data:
            return None

        return AlbumArt(
            data=data,
            mime_type="image/jpeg",
            url=artwork_url,
            source=self.name,
        )

    async def _search_itunes(self, query: str) -> str:
        """Search iTunes for album artwork URL.

        Args:
            query: Search query (artist + album/title).

        Returns:
            Artwork URL or empty string if not found.
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"{ITUNES_SEARCH_URL}?term={encoded_query}&media=music&entity=album&limit=1"

            # Run blocking request in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self._fetch_json, url)

            if result and result.get("resultCount", 0) > 0:
                artwork_url = result["results"][0].get("artworkUrl100", "")
                if artwork_url:
                    # Get higher resolution
                    return artwork_url.replace("100x100", ARTWORK_SIZE)

        except Exception as e:  # noqa: BLE001
            logger.debug("iTunes search failed for '%s': %s", query, e)

        return ""

    async def _download_image(self, url: str) -> bytes:
        """Download image from URL.

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
