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
    """收集 data/plugins 下所有文件到包，排除作者专用/敏感文件。

    ⚠️ 关键：datas 条目格式为 (源文件, 目标【目录】)，
       PyInstaller 会把源文件放进目标目录并保留文件名。
       目标绝不能写成完整文件路径，否则会产生 tools.py/tools.py 嵌套，
       导致插件管理器按 data/plugins/<id>/tools.py 找不到文件、全部加载失败。
    """
    base = os.path.join(specpath, 'data', 'plugins')
    files = []
    if os.path.isdir(base):
        for root, dirs, names in os.walk(base):
            rel_root = os.path.relpath(root, base)
            parts = rel_root.split(os.sep)
            # 跳过缓存目录与平台适配备份（variants/backup 带旧文件，不应进包）
            if '__pycache__' in parts or 'backup' in parts or '_source_backup' in parts:
                continue
            for n in names:
                low = n.lower()
                if low.endswith(_SENSITIVE_EXT) or low in _SENSITIVE_NAMES:
                    continue
                if n.endswith(('.pyc', '.pyo')):
                    continue
                p = os.path.join(root, n)
                # 目标必须是目录：data/plugins/<相对目录>/
                if rel_root == '.':
                    dest_dir = 'data/plugins'
                else:
                    dest_dir = os.path.join('data', 'plugins', rel_root)
                files.append((p, dest_dir))
    return files


a = Analysis(
    [os.path.join(SPECPATH, 'main.py')],
    pathex=[SPECPATH, os.path.join(SPECPATH, 'src')],
    binaries=[],
    datas=[(os.path.join(SPECPATH, 'config'), 'config'),
           (os.path.join(SPECPATH, 'data/logo'), 'data/logo'),
           (os.path.join(SPECPATH, 'data/__init__.py'), 'data/'),
           (os.path.join(SPECPATH, 'tools', 'web_autostart.py'), 'tools'),
           # 网页版前端静态资源（server.py WEB_STATIC_DIR 依赖，缺失会导致 404 web panel not found）
           (os.path.join(SPECPATH, 'src/web/static'), 'src/web/static')]
          + _collect_plugins(SPECPATH),
    hiddenimports=['src.web.server', 'src.web.routes.api_chat', 'src.web.routes', 'src.agent.web_console_tts', 'sqlalchemy', 'sqlalchemy.pool', 'sqlalchemy.ext.declarative', 'fastapi', 'uvicorn', 'uvicorn.loops', 'uvicorn.loops.auto', 'uvicorn.protocols', 'uvicorn.protocols.http', 'uvicorn.protocols.websockets', 'websockets', 'websockets.legacy', 'openai', 'httpx', 'yaml', 'apscheduler', 'loguru', 'pydantic', 'cryptography', 'PyQt6', 'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel', 'PyQt6.QtCharts', 'unidecode', 'slugify', 'mss', 'numpy', 'src.security', 'src.security.rsa_verify', 'src.security.license_verify', 'src.security.safe_modify', 'src.security.strings', 'src.security.auth_client', 'src.security.token_store', 'src.security.integrity', 'src.security.sec_config', 'src.security.device_fingerprint', 'src.security.entry_auth', 'src.security.plugin_guard', 'src.core.updater', 'src.agent.prompts', 'src.ui.login_dialog', 'src.ui.theme', 'src.ui.update_dialog', 'src.ui.welcome_wizard', 'src.ui.onboarding', 'src.ui.pro_status_widget', 'src.config.loader',
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
