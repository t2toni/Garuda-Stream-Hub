# -*- mode: python ; coding: utf-8 -*-
import sys
import os
from pathlib import Path

block_cipher = None

BASE_DIR = Path.cwd()

datas = [
    (str(BASE_DIR / 'src' / 'audio' / 'models'), os.path.join('src', 'audio', 'models')),
    (str(BASE_DIR / 'assets'), 'assets'),
]

# Add audio plugins if existing
plugins_dir = BASE_DIR / 'src' / 'audio' / 'plugins'
if plugins_dir.exists():
    datas.append((str(plugins_dir), os.path.join('src', 'audio', 'plugins')))

binaries = []
# Include native compiled pybind11 module if present
native_dir = BASE_DIR / 'src' / 'native'
for f in native_dir.glob('stream_native*'):
    if f.suffix in ('.so', '.pyd'):
        binaries.append((str(f), '.'))
        binaries.append((str(f), os.path.join('src', 'native')))

a = Analysis(
    [os.path.join('src', 'main.py')],
    pathex=[str(BASE_DIR), str(BASE_DIR / 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        'PyQt6',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'zeroconf',
        'zeroconf._utils.ipaddress',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'PySide2', 'PySide6', 'tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'IPython', 'notebook', 'pytest', 'sphinx', 'botocore'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='garuda-stream-hub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
