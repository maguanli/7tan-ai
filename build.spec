# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(Path('D:\7tan\7tanAI')), str(Path('D:\7tan\7tanAI/src'))],
    binaries=[],
    datas=[('config', 'config'), ('data/prompts', 'data/prompts'), ('data/plugins', 'data/plugins')],
    hiddenimports=['sqlalchemy', 'sqlalchemy.pool', 'sqlalchemy.ext.declarative', 'fastapi', 'uvicorn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.websockets', 'websockets', 'websockets.legacy', 'playwright', 'playwright.async_api', 'openai', 'httpx', 'yaml', 'apscheduler', 'loguru', 'watchfiles', 'pydantic', 'cryptography', 'aiofiles', 'PyQt6', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel', 'PyQt6.QtCharts', 'unidecode', 'slugify', 'mss', 'numpy', 'ui.video_editor', 'ui.video_editor.editor_window', 'ui.video_editor.ai_clip_engine', 'ui.video_editor.ai_dub_engine', 'ui.video_editor.ai_subtitle_engine', 'ui.video_editor.ai_video_maker', 'ui.video_editor.ai_video_panel', 'ui.video_editor.color_filter', 'ui.video_editor.commands', 'ui.video_editor.config', 'ui.video_editor.cover_ai_engine', 'ui.video_editor.cover_editor', 'ui.video_editor.cut_tool', 'ui.video_editor.data_models', 'ui.video_editor.editor_api', 'ui.video_editor.exporter', 'ui.video_editor.filter_panel', 'ui.video_editor.keyframe', 'ui.video_editor.keyframe_panel', 'ui.video_editor.media_bin', 'ui.video_editor.player', 'ui.video_editor.project_manager', 'ui.video_editor.recorder_overlay', 'ui.video_editor.recorder_settings', 'ui.video_editor.screen_recorder', 'ui.video_editor.styles', 'ui.video_editor.timeline', 'ui.video_editor.timeline_items', 'ui.video_editor.transition_engine', 'ui.video_editor.utils'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pdb',
        'IPython', 'jupyter', 'notebook',
        'matplotlib', 'pandas',
    ],
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
    name='7tan-editor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='7tan-editor',
)
