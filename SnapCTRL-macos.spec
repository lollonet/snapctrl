# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for SnapCTRL macOS app bundle."""

import sys
from pathlib import Path

block_cipher = None

# Project paths
project_root = Path(SPECPATH)
src_path = project_root / "src"
resources_path = project_root / "resources"

a = Analysis(
    [str(src_path / "snapctrl" / "__main__.py")],
    pathex=[str(src_path)],
    binaries=[],
    datas=[
        (str(resources_path / "icon.svg"), "resources"),
    ],
    hiddenimports=[
        "PySide6.QtSvg",
        "PySide6.QtSvgWidgets",
        # zeroconf for mDNS discovery
        "zeroconf",
        "zeroconf._utils.ipaddress",
        "zeroconf._handlers.answers",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="SnapCTRL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,  # Required for macOS
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="SnapCTRL",
)

# macOS app bundle
app = BUNDLE(
    coll,
    name="SnapCTRL.app",
    icon=str(resources_path / "SnapCTRL.icns"),
    bundle_identifier="local.snapctrl.SnapCTRL",
    info_plist={
        "CFBundleName": "SnapCTRL",
        "CFBundleDisplayName": "SnapCTRL",
        "CFBundleVersion": "0.2.6",
        "CFBundleShortVersionString": "0.2.6",
        "NSHighResolutionCapable": True,
        "NSRequiresAquaSystemAppearance": False,  # Support dark mode
        "LSMinimumSystemVersion": "10.15",
        "NSPrincipalClass": "NSApplication",
        "NSAppleScriptEnabled": False,
        # mDNS/Bonjour: required since macOS 11 for local network discovery
        "NSLocalNetworkUsageDescription": "SnapCTRL needs local network access to discover and control Snapcast servers.",
        "NSBonjourServices": ["_snapcast._tcp"],
    },
)
