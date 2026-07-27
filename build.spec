# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[str(Path('D:\7tan\7tanAI')), str(Path('D:\7tan\7tanAI/src'))],
    binaries=[],
    datas=[('config', 'config'), ('data/prompts', 'data/prompts'), ('data/plugins', 'data/plugins'), ('data/logo', 'data/logo')],
    hiddenimports=['sqlalchemy', 'sqlalchemy.pool', 'sqlalchemy.ext.declarative', 'fastapi', 'uvicorn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.websockets', 'websockets', 'websockets.legacy', 'playwright', 'playwright.async_api', 'openai', 'httpx', 'yaml', 'apscheduler', 'loguru', 'watchfiles', 'pydantic', 'cryptography', 'aiofiles', 'PyQt6', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel', 'PyQt6.QtCharts', 'unidecode', 'slugify', 'mss', 'numpy', 'src.security', 'src.security.rsa_verify', 'src.security.license_verify', 'src.security.safe_modify', 'src.security.strings', 'src.security.auth_client', 'src.security.token_store', 'src.security.trial_store', 'src.security.integrity'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pdb',
        'IPython', 'jupyter', 'notebook',
        'matplotlib', 'pandas',
        # --- 排除 ML/AI 包（项目不使用，torch c10.dll 损坏导致构建失败）---
        'torch', 'torchvision', 'torchaudio', 'torchtext',
        'onnxruntime', 'onnx', 'onnxconverter_common',
        'huggingface_hub', 'transformers', 'sentencepiece', 'tokenizers',
        'safetensors',
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
    icon=r'D:\7tan\7tanAI\data\logo\app_single.ico',
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
