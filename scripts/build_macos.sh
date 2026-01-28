#!/bin/bash
# Build SnapCTRL macOS app bundle

set -e



echo "Building SnapCTRL.app..."

# Clean previous builds
rm -rf build dist

# Build icon if needed
if [ ! -f resources/SnapCTRL.icns ]; then
    echo "Building icon..."
    uv run python scripts/build_icon.py
fi

# Build with PyInstaller
uv run pyinstaller SnapCTRL.spec --noconfirm

echo ""
echo "Build complete!"
echo "App bundle: dist/SnapCTRL.app"
echo ""
echo "To run: open dist/SnapCTRL.app"
echo "To install: cp -r dist/SnapCTRL.app /Applications/"
