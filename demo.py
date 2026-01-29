#!/usr/bin/env python
"""Quick demo of the Snapcast MVP UI."""

import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from snapctrl.ui.main_window import MainWindow
from snapctrl.models.group import Group
from snapctrl.models.source import Source


def main():
    app = QApplication(sys.argv)
    app.setOrganizationName("SnapcastMVP")
    app.setApplicationName("SnapcastController")

    window = MainWindow()
    window.resize(1000, 600)

    # Add sample data
    sample_sources = [
        Source(id="mpd", name="MPD", status="playing", stream_type="flac"),
        Source(id="spotify", name="Spotify", status="idle", stream_type="ogg"),
        Source(id="airplay", name="AirPlay", status="idle", stream_type="aac"),
    ]
    window.sources_panel.set_sources(sample_sources)

    sample_groups = [
        Group(
            id="g1",
            name="Living Room",
            stream_id="mpd",
            muted=False,
            client_ids=["client1", "client2"],
        ),
        Group(
            id="g2",
            name="Bedroom",
            stream_id="mpd",
            muted=True,
            client_ids=["client3"],
        ),
        Group(
            id="g3",
            name="Kitchen",
            stream_id="spotify",
            muted=False,
            client_ids=[],
        ),
    ]
    window.groups_panel.set_groups(sample_groups)

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
