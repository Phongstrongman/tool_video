# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for DouyinVoice Pro

Build command:
    pyinstaller build.spec

Output:
    dist/DouyinVoicePro.exe (single file, no console window)
"""

import sys
from pathlib import Path

block_cipher = None

# Base directory
BASE_DIR = Path('.')

# Data files to include
datas = [
    # Include entire src directory structure
    ('src', 'src'),
]

# Hidden imports (modules not auto-detected by PyInstaller)
hiddenimports = [
    # PyQt6 modules
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',

    # Core modules
    'src.core.api_client',
    'src.core.downloader',
    'src.core.audio_extractor',
    'src.core.speech_to_text',
    'src.core.translator',
    'src.core.text_to_speech',
    'src.core.video_merger',
    'src.core.video_effects',
    'src.core.text_overlay',

    # UI modules
    'src.ui.main_window',
    'src.ui.login_dialog',
    'src.ui.styles',

    # Workers
    'src.workers.async_workers',

    # Utils
    'src.utils.config',
    'src.utils.helpers',

    # Speech-to-Text engines
    'whisper',
    'assemblyai',
    'groq',

    # Text-to-Speech
    'edge_tts',
    'gtts',
    'google.genai',

    # Translation
    'deep_translator',

    # Video/Audio
    'pydub',
    'yt_dlp',

    # HTTP
    'requests',
    'urllib3',

    # Standard library
    'csv',
    'datetime',
    'pathlib',
    'json',
    'subprocess',
]

# Analysis
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude server folder (stays on your computer only)
        'server',
        'server.app',
        'server.database',
        'server.config',
        'server.generate_license',

        # Exclude unnecessary modules to reduce .exe size
        'matplotlib',
        'numpy.testing',
        'tkinter',
        'unittest',
        'pytest',
        'test',
        'tests',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# PYZ (Python zip archive)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

# EXE configuration - Single file executable
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DouyinVoicePro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Compress with UPX for smaller size
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Hide console window (windowed mode)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Icon (optional - uncomment if you have icon.ico)
    # icon='icon.ico',
)
