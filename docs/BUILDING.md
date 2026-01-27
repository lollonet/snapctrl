# Building SnapCTRL

This document describes how to build SnapCTRL for distribution on macOS, Windows, and Linux.

## Prerequisites

- Python 3.11+ with uv package manager
- PyInstaller (included in dev dependencies)
- Platform-specific tools (see below)

## Quick Build

```bash
# Install dependencies
uv sync --all-extras

# Run platform-specific build
uv run python scripts/build.py
```

This will automatically detect your platform and create the appropriate distribution.

## Platform-Specific Instructions

### macOS

**Requirements:**
- macOS 10.15 or later
- Xcode Command Line Tools

**Build:**
```bash
uv run python scripts/build.py
```

**Output:**
- `dist/SnapCTRL.app` - Application bundle
- `dist/SnapCTRL-0.1.0-macOS.dmg` - Disk image for distribution

**Manual DMG creation:**
```bash
uv run pyinstaller SnapCTRL.spec --clean --noconfirm
cd dist
hdiutil create -volname "SnapCTRL" -srcfolder SnapCTRL.app -ov -format UDZO SnapCTRL-0.1.0-macOS.dmg
```

### Windows

**Requirements:**
- Windows 10 or later
- Python 3.11+ with uv

**Build:**
```bash
uv run python scripts/build.py
```

**Output:**
- `dist/SnapCTRL/` - Portable application folder
- `dist/SnapCTRL-0.1.0-Windows.zip` - ZIP archive for distribution

**Manual build:**
```bash
uv run pyinstaller SnapCTRL-windows.spec --clean --noconfirm
```

### Linux

**Requirements:**
- Ubuntu 20.04+ / Debian 11+ or equivalent
- Python 3.11+ with uv
- Qt dependencies: `sudo apt install libxcb-cursor0`

**Build:**
```bash
uv run python scripts/build.py
```

**Output:**
- `dist/SnapCTRL/` - Portable application folder
- `dist/SnapCTRL-0.1.0-Linux.tar.gz` - Tarball for distribution

**Manual build:**
```bash
uv run pyinstaller SnapCTRL-linux.spec --clean --noconfirm
```

## Build Files

| File | Platform | Description |
|------|----------|-------------|
| `SnapCTRL.spec` | macOS | PyInstaller spec with .app bundle |
| `SnapCTRL-windows.spec` | Windows | PyInstaller spec with .exe |
| `SnapCTRL-linux.spec` | Linux | PyInstaller spec for Linux |
| `scripts/build.py` | All | Automated build script |

## Resources

| File | Description |
|------|-------------|
| `resources/icon.svg` | Source icon (vector) |
| `resources/SnapCTRL.icns` | macOS icon bundle |
| `resources/SnapCTRL.ico` | Windows icon |

## Troubleshooting

### macOS: "App is damaged"
The app is not signed. Right-click → Open to bypass Gatekeeper on first run.

### Windows: Missing DLLs
Ensure Visual C++ Redistributable is installed.

### Linux: Qt platform plugin error
Install Qt platform dependencies:
```bash
sudo apt install libxcb-cursor0 libxkbcommon0
```

### All platforms: Large binary size
PySide6 bundles the entire Qt framework. Size is typically:
- macOS: ~100MB (DMG: ~45MB)
- Windows: ~80MB (ZIP: ~35MB)
- Linux: ~90MB (tar.gz: ~40MB)

## CI/CD

For automated builds, use GitHub Actions with platform-specific runners:

```yaml
strategy:
  matrix:
    os: [macos-latest, windows-latest, ubuntu-latest]
```

See `.github/workflows/` for examples.
