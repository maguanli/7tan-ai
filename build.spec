# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# cryptography 浣跨敤寤惰繜瀵煎叆瀛愭ā鍧楋紙濡?ciphers.aead锛夛紝闈欐€佸垎鏋愬父婕忔姄锛屽叏閲忔敹闆?
_crypto_submods = collect_submodules('cryptography')

a = Analysis(
    [os.path.join(SPECPATH, 'main.py')],
    pathex=[SPECPATH, os.path.join(SPECPATH, 'src')],
    binaries=[],
    datas=[(os.path.join(SPECPATH, 'config'), 'config'), (os.path.join(SPECPATH, 'data/prompts'), 'data/prompts'), (os.path.join(SPECPATH, 'data/plugins'), 'data/plugins'), (os.path.join(SPECPATH, 'data/logo'), 'data/logo')],
    hiddenimports=['sqlalchemy', 'sqlalchemy.pool', 'sqlalchemy.ext.declarative', 'fastapi', 'uvicorn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.websockets', 'websockets', 'websockets.legacy', 'playwright', 'playwright.async_api', 'openai', 'httpx', 'yaml', 'apscheduler', 'loguru', 'pydantic', 'cryptography', 'PyQt6', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel', 'PyQt6.QtCharts', 'unidecode', 'slugify', 'mss', 'numpy', 'src.security', 'src.security.rsa_verify', 'src.security.license_verify', 'src.security.safe_modify', 'src.security.strings', 'src.security.auth_client', 'src.security.token_store', 'src.security.trial_store', 'src.security.integrity', *_crypto_submods],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pdb',
        'IPython', 'jupyter', 'notebook',
        'matplotlib', 'pandas',
        # --- 鎺掗櫎 ML/AI 鍖咃紙椤圭洰涓嶄娇鐢紝torch c10.dll 鎹熷潖瀵艰嚧鏋勫缓澶辫触锛?--
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
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(SPECPATH, 'data', 'logo', 'app_single.ico'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='7tan-editor',
)
