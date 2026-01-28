"""MPD client module.

This module provides an async MPD client for fetching track metadata
and album art. It's designed for future expansion into a full MPD controller.

Example:
    from snapcast_mvp.api.mpd import MpdClient

    async with MpdClient("192.168.1.100") as client:
        status = await client.status()
        track = await client.currentsong()
        art = await client.get_album_art(track.file)
"""

from snapcast_mvp.api.mpd.client import MpdClient, MpdConnectionError
from snapcast_mvp.api.mpd.protocol import MpdError
from snapcast_mvp.api.mpd.types import MpdAlbumArt, MpdStatus, MpdTrack

__all__ = [
    "MpdClient",
    "MpdConnectionError",
    "MpdError",
    "MpdAlbumArt",
    "MpdStatus",
    "MpdTrack",
]
