# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for SnapCTRL Windows executable."""

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
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(resources_path / "SnapCTRL.ico"),  # Windows icon
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
