#!/usr/bin/env python3
"""Convert SVG icon to macOS .icns format using PySide6."""

import subprocess
import tempfile
from pathlib import Path

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer


def svg_to_icns(svg_path: Path, icns_path: Path) -> None:
    """Convert SVG to macOS .icns format.

    Args:
        svg_path: Path to source SVG file.
        icns_path: Path to output .icns file.
    """
    # Initialize Qt (required for rendering)
    app = QGuiApplication([])  # noqa: F841

    renderer = QSvgRenderer(str(svg_path))
    if not renderer.isValid():
        raise ValueError(f"Failed to load SVG: {svg_path}")

    # macOS icon sizes
    sizes = [16, 32, 64, 128, 256, 512, 1024]

    with tempfile.TemporaryDirectory() as tmpdir:
        iconset_dir = Path(tmpdir) / "SnapCTRL.iconset"
        iconset_dir.mkdir()

        for size in sizes:
            # Create image and render SVG
            image = QImage(QSize(size, size), QImage.Format.Format_ARGB32)
            image.fill(Qt.GlobalColor.transparent)

            painter = QPainter(image)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            renderer.render(painter)
            painter.end()

            # Save standard resolution
            if size <= 512:
                png_path = iconset_dir / f"icon_{size}x{size}.png"
                image.save(str(png_path), "PNG")

            # Save as 2x retina for smaller base size
            if size >= 32:
                base_size = size // 2
                if base_size in [16, 32, 128, 256, 512]:
                    png_path = iconset_dir / f"icon_{base_size}x{base_size}@2x.png"
                    image.save(str(png_path), "PNG")

        # Use iconutil to create .icns (macOS only)
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(iconset_dir), "-o", str(icns_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"iconutil error: {result.stderr}")
            raise RuntimeError("iconutil failed")

    print(f"Created {icns_path}")


def main() -> None:
    """Build the macOS icon."""
    project_root = Path(__file__).parent.parent
    svg_path = project_root / "resources" / "icon.svg"
    icns_path = project_root / "resources" / "SnapCTRL.icns"

    if not svg_path.exists():
        print(f"Error: {svg_path} not found")
        return

    svg_to_icns(svg_path, icns_path)


if __name__ == "__main__":
    main()
