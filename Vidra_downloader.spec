# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

a = Analysis(
    ['vidra_main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('ffmpeg/bin/ffmpeg.exe', 'ffmpeg/bin'),
        ('vidra_settings.json', '.'),
        ('requirement.txt', '.'),
        ('splash.png', '.'),
        ('icon.ico', '.'),  # Optional, just to preserve it
    ],
    hiddenimports=collect_submodules('yt_dlp'),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Vidra_downloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
    splash='splash.png'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Vidra_downloader'
)
