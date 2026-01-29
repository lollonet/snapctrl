"""MPD protocol parsing utilities.

MPD uses a simple line-based text protocol:
- Commands are sent as plain text lines
- Responses are key-value pairs: "key: value"
- Responses end with "OK" or "ACK [error] {command} message"
- Binary responses (albumart, readpicture) have a special format

Reference: https://mpd.readthedocs.io/en/stable/protocol.html
"""

import re
from dataclasses import fields
from typing import Any

from snapctrl.api.mpd.types import MpdAlbumArt, MpdStatus, MpdTrack


class MpdError(Exception):
    """MPD protocol error."""

    def __init__(self, code: int, command: str, message: str) -> None:
        self.code = code
        self.command = command
        self.message = message
        super().__init__(f"MPD error {code} in {command}: {message}")


# Pattern for ACK responses: ACK [error@command_listNum] {current_command} message_text
ACK_PATTERN = re.compile(r"ACK \[(\d+)@\d+\] \{(\w*)\} (.+)")

# MPD key name mappings to dataclass field names
_TRACK_KEY_MAP: dict[str, str] = {
    "file": "file",
    "title": "title",
    "artist": "artist",
    "album": "album",
    "albumartist": "album_artist",
    "time": "duration",
    "duration": "duration",
    "track": "track",
    "date": "date",
    "genre": "genre",
    "pos": "pos",
    "id": "id",
}

_STATUS_KEY_MAP: dict[str, str] = {
    "state": "state",
    "volume": "volume",
    "repeat": "repeat",
    "random": "random",
    "single": "single",
    "consume": "consume",
    "song": "song",
    "songid": "song_id",
    "elapsed": "elapsed",
    "duration": "duration",
    "time": "_time",  # Special: "elapsed:duration" format
    "bitrate": "bitrate",
    "audio": "audio",
    "error": "error",
}


def parse_response(lines: list[str]) -> dict[str, str]:
    """Parse MPD response lines into a key-value dict.

    Args:
        lines: Response lines (without the final OK/ACK).

    Returns:
        Dictionary of key-value pairs.

    Raises:
        MpdError: If response is an ACK error.
    """
    result: dict[str, str] = {}

    for line in lines:
        # Check for ACK error
        if line.startswith("ACK "):
            match = ACK_PATTERN.match(line)
            if match:
                code = int(match.group(1))
                command = match.group(2)
                message = match.group(3)
                raise MpdError(code, command, message)
            raise MpdError(0, "", line)

        # Skip OK line
        if line == "OK":
            continue

        # Parse key: value
        if ": " in line:
            key, value = line.split(": ", 1)
            result[key.lower()] = value

    return result


def parse_track(data: dict[str, str]) -> MpdTrack:
    """Parse track data into MpdTrack.

    Args:
        data: Key-value dict from parse_response.

    Returns:
        MpdTrack instance.
    """
    kwargs: dict[str, Any] = {}
    field_types = {f.name: f.type for f in fields(MpdTrack)}

    for mpd_key, field_name in _TRACK_KEY_MAP.items():
        if mpd_key in data:
            value = data[mpd_key]
            field_type = field_types.get(field_name)

            if field_type is int:
                kwargs[field_name] = int(value)
            elif field_type is float:
                kwargs[field_name] = float(value)
            else:
                kwargs[field_name] = value

    # file is required
    if "file" not in kwargs:
        kwargs["file"] = ""

    return MpdTrack(**kwargs)


def parse_status(data: dict[str, str]) -> MpdStatus:
    """Parse status data into MpdStatus.

    Args:
        data: Key-value dict from parse_response.

    Returns:
        MpdStatus instance.
    """
    kwargs: dict[str, Any] = {}
    field_types = {f.name: f.type for f in fields(MpdStatus)}

    for mpd_key, field_name in _STATUS_KEY_MAP.items():
        if mpd_key not in data:
            continue

        value = data[mpd_key]

        # Special handling for "time" which is "elapsed:duration"
        if field_name == "_time" and ":" in value:
            elapsed_str, duration_str = value.split(":", 1)
            kwargs["elapsed"] = float(elapsed_str)
            kwargs["duration"] = float(duration_str)
            continue

        field_type = field_types.get(field_name)

        if field_type is int:
            kwargs[field_name] = int(value)
        elif field_type is float:
            kwargs[field_name] = float(value)
        elif field_type is bool:
            kwargs[field_name] = value == "1"
        else:
            kwargs[field_name] = value

    return MpdStatus(**kwargs)


def parse_binary_response(header_lines: list[str], binary_data: bytes, uri: str) -> MpdAlbumArt:
    """Parse binary response (albumart/readpicture).

    Args:
        header_lines: Response header lines before binary data.
        binary_data: The binary image data.
        uri: The file URI this art is associated with.

    Returns:
        MpdAlbumArt instance.
    """
    header = parse_response(header_lines)
    size = int(header.get("size", "0"))
    mime_type = header.get("type", "")

    return MpdAlbumArt(
        uri=uri,
        data=binary_data,
        mime_type=mime_type,
        size=size,
    )


def escape_arg(arg: str) -> str:
    """Escape an argument for MPD command.

    MPD requires arguments with spaces or special chars to be quoted.
    Inside quotes, backslash and double-quote must be escaped.

    Args:
        arg: The argument to escape.

    Returns:
        Escaped argument, quoted if necessary.
    """
    # If no special characters, return as-is
    if arg and not any(c in arg for c in ' "\t\n\\'):
        return arg

    # Escape backslashes and quotes, wrap in quotes
    escaped = arg.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def format_command(command: str, *args: str) -> str:
    """Format an MPD command with arguments.

    Args:
        command: The MPD command name.
        *args: Command arguments.

    Returns:
        Formatted command string (without newline).
    """
    if not args:
        return command
    escaped_args = [escape_arg(arg) for arg in args]
    return f"{command} {' '.join(escaped_args)}"
