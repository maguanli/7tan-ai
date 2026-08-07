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
    datas=[(os.path.join(SPECPATH, 'config'), 'config'), (os.path.join(SPECPATH, 'data/plugins'), 'data/plugins'), (os.path.join(SPECPATH, 'data/logo'), 'data/logo'), (os.path.join(SPECPATH, 'data/__init__.py'), 'data/')],
    hiddenimports=['sqlalchemy', 'sqlalchemy.pool', 'sqlalchemy.ext.declarative', 'fastapi', 'uvicorn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.websockets', 'websockets', 'websockets.legacy', 'openai', 'httpx', 'yaml', 'apscheduler', 'loguru', 'pydantic', 'cryptography', 'PyQt6', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel', 'PyQt6.QtCharts', 'unidecode', 'slugify', 'mss', 'numpy', 'src.security', 'src.security.rsa_verify', 'src.security.license_verify', 'src.security.safe_modify', 'src.security.strings', 'src.security.auth_client', 'src.security.token_store', 'src.security.trial_store', 'src.security.integrity', 'src.security.sec_config', 'src.security.device_fingerprint', 'src.security.entry_auth', 'src.security.plugin_guard', 'src.core.updater', 'src.agent.prompts', 'src.ui.login_dialog', 'src.ui.theme', 'src.ui.update_dialog', 'src.ui.welcome_wizard', 'src.ui.onboarding', 'src.ui.pro_status_widget', 'src.config.loader',
        'piper', 'piper.voice', 'edge_tts', 'onnxruntime',
        'data.plugins.tts_piper.tools',
        *_crypto_submods],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter', 'unittest', 'test', 'pdb',
        'IPython', 'jupyter', 'notebook',
        'matplotlib', 'pandas',
        # --- 鎺掗櫎 ML/AI 鍖咃紙椤圭洰涓嶄娇鐢紝torch c10.dll 鎹熷潖瀵艰嚧鏋勫缓澶辫触锛?--
        'torch', 'torchvision', 'torchaudio', 'torchtext',
        # --- 排除代码中零引用的重型库（瘦身：playwright/cv2/ddddocr 等）---
        'playwright', 'cv2', 'ddddocr', 'ctranslate2', 'winsdk', 'winrt',
        'moviepy', 'pydub', 'av', 'speech_recognition', 'selenium',
        'onnx', 'onnxconverter_common',
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
    version=os.path.join(SPECPATH, 'file_version_info.txt'),
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
