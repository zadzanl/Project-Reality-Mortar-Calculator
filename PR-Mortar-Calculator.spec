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
from PyInstaller.utils.hooks import collect_dynamic_libs
import os

# Get the repository root directory (directory containing this spec file)
root_dir = os.path.abspath(os.getcwd())

# Collect all Flask templates and static files
d = []
# Include UI templates and static assets
d.append((os.path.join(root_dir, 'calculator', 'templates'), 'calculator/templates'))
d.append((os.path.join(root_dir, 'calculator', 'static'), 'calculator/static'))
# Include processed maps (only .gz, .png, and metadata.json files)
d.append((os.path.join(root_dir, 'processed_maps'), 'processed_maps'))
datas = d

# Collect Flask data files (Jinja2 templates, etc.)
datas += collect_data_files('flask')
datas += collect_data_files('werkzeug')

# Collect all Flask and Werkzeug submodules
hiddenimports = collect_submodules('flask')
hiddenimports += collect_submodules('werkzeug')
hiddenimports += collect_submodules('jinja2')
hiddenimports += ['PIL._tkinter_finder']  # Pillow support
hiddenimports += ['jaraco.text']

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

# Filter out uncompressed heightmap.json files (keep only .json.gz)
# This ensures only compressed heightmaps are bundled
a.datas = [(dest, src, typ) for dest, src, typ in a.datas 
           if not (dest.startswith('processed_maps') and dest.endswith('heightmap.json'))]

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
    upx_exclude=[],  # Don't exclude any files from UPX compression
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
    upx_exclude=[],  # Compress all binaries with UPX
    name='PR-Mortar-Calculator'
)
