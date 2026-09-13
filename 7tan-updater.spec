# -*- mode: python ; coding: utf-8 -*-
# ============================================================
# 7tan-updater PyInstaller Spec (Build #12 - 精简版)
# 策略：排除未用模块 + 构建后脚本清理多余 DLL
# 构建命令（必须带 distpath/workpath 否则跑到 C 盘）：
#   python -m PyInstaller 7tan-updater.spec --noconfirm --distpath dist --workpath build
# ============================================================
from PyInstaller.utils.hooks import collect_submodules, collect_data_files

datas = [
    ('data/prompts', 'data/prompts'),
    ('config/config.yaml', 'config'),
    ('config/sensitive_words.txt', 'config'),
    ('.env.example', '.'),
]
binaries = []
hiddenimports = []

# ---- 只收集实际使用的 PyQt6 子模块 ----
for mod in ['PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtCharts',
            'PyQt6.QtNetwork', 'PyQt6.QtOpenGL', 'PyQt6.QtOpenGLWidgets', 'PyQt6.QtXml',
            'PyQt6.QtWebSockets', 'PyQt6.QtSvg', 'PyQt6.QtPrintSupport',
            'PyQt6.QtWebEngineWidgets', 'PyQt6.QtWebEngineCore', 'PyQt6.QtWebChannel']:
    hiddenimports += collect_submodules(mod)
    datas += collect_data_files(mod)

# ---- 其他必需模块 ----
hiddenimports += collect_submodules('loguru')
datas += collect_data_files('loguru')
hiddenimports += collect_submodules('encodings')
hiddenimports += ['uvicorn', 'fastapi', 'apscheduler', 'yaml', 'dotenv', 'requests', 'openai']

# ---- 排除未用的 PyQt6 模块 (Python imports) ----
excluded_modules = [
    'PyQt6.QtPdf', 'PyQt6.QtPdfWidgets', 'PyQt6.QtWebView',
    'PyQt6.QtQuick3D', 'PyQt6.QtQuickWidgets',
    'PyQt6.QtBluetooth', 'PyQt6.QtNfc', 'PyQt6.QtSensors',
    'PyQt6.QtPositioning', 'PyQt6.QtLocation',
    'PyQt6.QtMultimedia', 'PyQt6.QtMultimediaWidgets',
    'PyQt6.QtSerialPort', 'PyQt6.QtSerialBus',
    'PyQt6.QtSql', 'PyQt6.QtSvgWidgets',
    'PyQt6.QtTest', 'PyQt6.QtHelp', 'PyQt6.QtDesigner', 'PyQt6.QtUiTools',
    'PyQt6.QtStateMachine', 'PyQt6.Qt3DCore', 'PyQt6.Qt3DRender',
    'PyQt6.Qt3DInput', 'PyQt6.Qt3DAnimation', 'PyQt6.Qt3DExtras',
    'PyQt6.Qt3DLogic', 'PyQt6.QtDataVisualization',
    'PyQt6.QtSpatialAudio', 'PyQt6.QtTextToSpeech',
    'PyQt6.QtRemoteObjects', 'PyQt6.QtHttpServer', 'PyQt6.QtGraphs',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_modules,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='7tan-updater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='7tan-updater',
)
