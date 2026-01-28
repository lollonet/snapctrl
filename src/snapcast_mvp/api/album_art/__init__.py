"""Album art provider module with fallback chain.

Provides album art from multiple sources:
1. iTunes Search API - Best coverage, fast
2. MusicBrainz Cover Art Archive - Community-driven, free

Adapted from rpi-snapclient-usb metadata-service.
"""

from snapcast_mvp.api.album_art.itunes import ITunesAlbumArtProvider
from snapcast_mvp.api.album_art.musicbrainz import MusicBrainzAlbumArtProvider
from snapcast_mvp.api.album_art.provider import (
    AlbumArt,
    AlbumArtProvider,
    FallbackAlbumArtProvider,
)

__all__ = [
    "AlbumArt",
    "AlbumArtProvider",
    "FallbackAlbumArtProvider",
    "ITunesAlbumArtProvider",
    "MusicBrainzAlbumArtProvider",
]
