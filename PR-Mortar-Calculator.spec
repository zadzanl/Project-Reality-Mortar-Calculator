# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller Specification File for Project Reality Mortar Calculator

This file configures how PyInstaller bundles the Flask application into
a standalone executable with all dependencies and data files.

Build command:
    pyinstaller PR-Mortar-Calculator.spec

Output:
    dist/PR-Mortar-Calculator/  - Executable and dependencies
"""

from PyInstaller.utils.hooks import collect_data_files, collect_submodules
import os

# Get the root directory
root_dir = os.path.abspath(SPECPATH)

# Collect all Flask templates and static files
datas = [
    (os.path.join(root_dir, 'calculator', 'templates'), 'calculator/templates'),
    (os.path.join(root_dir, 'calculator', 'static'), 'calculator/static'),
    (os.path.join(root_dir, 'processed_maps'), 'processed_maps'),
]

# Collect Flask data files (Jinja2 templates, etc.)
datas += collect_data_files('flask')
datas += collect_data_files('werkzeug')

# Collect all Flask and Werkzeug submodules
hiddenimports = collect_submodules('flask')
hiddenimports += collect_submodules('werkzeug')
hiddenimports += collect_submodules('jinja2')
hiddenimports += ['PIL._tkinter_finder']  # Pillow support

block_cipher = None

a = Analysis(
    [os.path.join(root_dir, 'calculator', 'server.py')],
    pathex=[root_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude unnecessary modules to reduce size
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'numpy',
        'pytest',
        'setuptools',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PR-Mortar-Calculator',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # Show console for server logs
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you create one: 'calculator/static/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PR-Mortar-Calculator'
)
