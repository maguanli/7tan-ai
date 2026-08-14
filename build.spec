# -*- mode: python ; coding: utf-8 -*-
# 7Tan Editor PyInstaller 构建配置
# 安全说明：data/plugins 收集时排除作者专用/敏感文件（私钥、发码脚本等），
#           确保发布包不含 private_key.pem / gen_license.py
import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# cryptography 使用延迟导入子模块（如 ciphers.aead），静态分析常漏抓，全量收集
_crypto_submods = collect_submodules('cryptography')

_SENSITIVE_EXT = ('.pem', '.key', '.p12', '.pfx')
_SENSITIVE_NAMES = ('gen_license.py',)


def _collect_plugins(specpath):
    """收集 data/plugins 下所有文件到包，排除作者专用/敏感文件。"""
    base = os.path.join(specpath, 'data', 'plugins')
    files = []
    if os.path.isdir(base):
        for root, dirs, names in os.walk(base):
            for n in names:
                low = n.lower()
                if low.endswith(_SENSITIVE_EXT) or low in _SENSITIVE_NAMES:
                    continue
                p = os.path.join(root, n)
                rel = os.path.relpath(p, base)
                files.append((p, os.path.join('data', 'plugins', rel)))
    return files


a = Analysis(
    [os.path.join(SPECPATH, 'main.py')],
    pathex=[SPECPATH, os.path.join(SPECPATH, 'src')],
    binaries=[],
    datas=[(os.path.join(SPECPATH, 'config'), 'config'),
           (os.path.join(SPECPATH, 'data/logo'), 'data/logo'),
           (os.path.join(SPECPATH, 'data/__init__.py'), 'data/')]
          + _collect_plugins(SPECPATH),
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
        # --- 排除 ML/AI 包（项目不使用，torch c10.dll 损坏导致构建失败）---
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
