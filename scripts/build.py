#!/usr/bin/env python3
"""Build script for SnapCTRL - creates platform-specific distributions."""

import platform
import shutil
import subprocess
import sys
from pathlib import Path

VERSION = "0.1.0"
PROJECT_ROOT = Path(__file__).parent.parent


def run(cmd: list[str], **kwargs) -> None:
    """Run a command and exit on failure."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        sys.exit(result.returncode)


def clean() -> None:
    """Remove build artifacts."""
    for path in ["build", "dist"]:
        full_path = PROJECT_ROOT / path
        if full_path.exists():
            print(f"Removing {full_path}")
            shutil.rmtree(full_path)


def build_macos() -> None:
    """Build macOS .app bundle and .dmg."""
    print("\n=== Building macOS app ===")

    spec_file = PROJECT_ROOT / "SnapCTRL.spec"
    if not spec_file.exists():
        print(f"Error: {spec_file} not found")
        sys.exit(1)

    run(["pyinstaller", str(spec_file), "--clean", "--noconfirm"])

    # Create DMG
    dist_dir = PROJECT_ROOT / "dist"
    app_path = dist_dir / "SnapCTRL.app"
    dmg_path = dist_dir / f"SnapCTRL-{VERSION}-macOS.dmg"

    if app_path.exists():
        print(f"\nCreating DMG: {dmg_path.name}")
        run([
            "hdiutil", "create",
            "-volname", "SnapCTRL",
            "-srcfolder", str(app_path),
            "-ov", "-format", "UDZO",
            str(dmg_path)
        ])
        print(f"\n✓ macOS build complete: {dmg_path}")
    else:
        print("Error: App bundle not created")
        sys.exit(1)


def build_windows() -> None:
    """Build Windows executable."""
    print("\n=== Building Windows executable ===")

    spec_file = PROJECT_ROOT / "SnapCTRL-windows.spec"
    if not spec_file.exists():
        print(f"Error: {spec_file} not found")
        sys.exit(1)

    run(["pyinstaller", str(spec_file), "--clean", "--noconfirm"])

    dist_dir = PROJECT_ROOT / "dist" / "SnapCTRL"
    if dist_dir.exists():
        # Create zip archive
        zip_name = f"SnapCTRL-{VERSION}-Windows"
        zip_path = PROJECT_ROOT / "dist" / zip_name
        print(f"\nCreating archive: {zip_name}.zip")
        shutil.make_archive(str(zip_path), "zip", str(dist_dir.parent), "SnapCTRL")
        print(f"\n✓ Windows build complete: {zip_path}.zip")
    else:
        print("Error: Windows build not created")
        sys.exit(1)


def build_linux() -> None:
    """Build Linux executable."""
    print("\n=== Building Linux executable ===")

    spec_file = PROJECT_ROOT / "SnapCTRL-linux.spec"
    if not spec_file.exists():
        print(f"Error: {spec_file} not found")
        sys.exit(1)

    run(["pyinstaller", str(spec_file), "--clean", "--noconfirm"])

    dist_dir = PROJECT_ROOT / "dist" / "SnapCTRL"
    if dist_dir.exists():
        # Create tar.gz archive
        archive_name = f"SnapCTRL-{VERSION}-Linux"
        archive_path = PROJECT_ROOT / "dist" / archive_name
        print(f"\nCreating archive: {archive_name}.tar.gz")
        shutil.make_archive(str(archive_path), "gztar", str(dist_dir.parent), "SnapCTRL")
        print(f"\n✓ Linux build complete: {archive_path}.tar.gz")
    else:
        print("Error: Linux build not created")
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    system = platform.system()

    print(f"SnapCTRL Build Script v{VERSION}")
    print(f"Platform: {system}")
    print(f"Project root: {PROJECT_ROOT}")

    # Clean previous builds
    clean()

    if system == "Darwin":
        build_macos()
    elif system == "Windows":
        build_windows()
    elif system == "Linux":
        build_linux()
    else:
        print(f"Unsupported platform: {system}")
        sys.exit(1)


if __name__ == "__main__":
    main()
