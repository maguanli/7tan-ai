# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 — 7坛AI小编
使用: pyinstaller build.spec
输出: dist/7tan-updater/7tan-updater.exe (onedir 模式, ~300-500MB 含 Chromium)
"""
import sys
from pathlib import Path

block_cipher = None
PROJECT_ROOT = Path(SPECPATH)

# ── 隐藏导入（PyInstaller 无法自动检测的模块） ──
hidden_imports = [
    # PyQt6 — 原生控件，无 WebEngine 依赖
    'PyQt6',
    'PyQt6.QtCore',
    'PyQt6.QtGui',
    'PyQt6.QtWidgets',
    'PyQt6.QtNetwork',
    'PyQt6.QtWebSockets',
    'PyQt6.QtCharts',
    'PyQt6.QtPrintSupport',
    'PyQt6_Charts',

    # ASGI / uvicorn
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.wsproto_impl',
    'uvicorn.logging',
    'websockets',

    # SQL
    'aiosqlite',
    'sqlalchemy.dialects.sqlite',

    # APScheduler
    'apscheduler.triggers.cron',
    'apscheduler.triggers.interval',
    'apscheduler.executors.pool',
    'apscheduler.jobstores.memory',
    'apscheduler.schedulers.asyncio',

    # Playwright (browser binary 通过运行时检查安装)
    'playwright',
    'playwright.async_api',
    'playwright.sync_api',

    # 其他
    'yaml',
    'loguru',
    'dotenv',
    'yaml',
    'PIL.Image',
    'cryptography',
    'httpx',
    'bs4',
    'lxml',
    'feedparser',
    'tqdm',

    # src 模块（确保所有子模块被包含）
    'src',
    'src.cli',
    'src.config',
    'src.config.loader',
    'src.database',
    'src.database.db',
    'src.scheduler',
    'src.scheduler.scheduler',
    'src.ui',
    'src.ui.app',
    'src.web',
    'src.web.server',
    'src.web.ws',
    'src.web.routes',
    'src.web.routes.api_resources',
    'src.web.routes.api_tasks',
    'src.web.routes.api_sources',
    'src.web.routes.api_stats',
    'src.web.routes.api_settings',
    'src.web.routes.api_chat',
    'src.agent',
    'src.agent.agent_loop',
    'src.agent.conversation',
    'src.tools',
    'src.tools.monitor_tools',
    'src.utils',
    'src.utils.logger',
    'src.pipeline',
    'src.pipeline.pipeline',
    'src.pipeline.task_queue',
    'src.security',
    'src.security.integrity',
]

# ── 数据文件（静态资源 + 模板 + 配置） ──
datas = [
    # 前端静态文件
    (str(PROJECT_ROOT / "src" / "web" / "static" / "css"),
     "src/web/static/css"),
    (str(PROJECT_ROOT / "src" / "web" / "static" / "js"),
     "src/web/static/js"),
    # 前端模板
    (str(PROJECT_ROOT / "src" / "web" / "templates" / "index.html"),
     "src/web/templates"),
    # 配置模板（首次运行时会复制到 exe 同级 config/ 目录）
    (str(PROJECT_ROOT / "config" / "config.yaml"),
     "config"),
    (str(PROJECT_ROOT / "config" / "sensitive_words.txt"),
     "config"),
    # .env.example
    (str(PROJECT_ROOT / ".env.example"),
     "."),
]

a = Analysis(
    [str(PROJECT_ROOT / "main.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'jupyter',
        'IPython',
        'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ═══════════════════════════════════════════
# onedir 模式：打包成一个文件夹
# exe 在 dist/7tan-updater/7tan-updater.exe
# ═══════════════════════════════════════════
exe = EXE(
    pyz,
    a.scripts,
    [],   # binaries 仅在 COLLECT 中，避免 PKG 归档解压失败
    a.zipfiles,
    [],   # datas 仅在 COLLECT 中
    [],
    name='7tan-updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI 模式不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / "tools" / "icon.ico") if (PROJECT_ROOT / "tools" / "icon.ico").exists() else None,
)

# 收集到 COLLECT（onedir 模式的输出文件夹结构）
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='7tan-updater',
)
