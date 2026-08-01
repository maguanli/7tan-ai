"""
构建打包工具 — PyInstaller --onedir
生成独立的 .exe 发布目录
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path

# 项目根目录
ROOT = Path(__file__).parent.parent
DIST = ROOT / "dist"
BUILD = ROOT / "build"
SPEC = ROOT / "build.spec"


def clean():
    """清理旧的构建目录"""
    for d in [DIST, BUILD, ROOT / "__pycache__"]:
        if d.exists():
            shutil.rmtree(d)
            print(f"🗑️ 清理: {d}")

    spec_alt = ROOT / "7tan-auto-updater.spec"
    if spec_alt.exists():
        spec_alt.unlink()


def generate_spec():
    """生成 PyInstaller spec 文件"""
    hidden_imports = [
        "sqlalchemy", "sqlalchemy.pool", "sqlalchemy.ext.declarative",
        "fastapi", "uvicorn", "uvicorn.loops", "uvicorn.loops.auto",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.websockets",
        "websockets", "websockets.legacy",
        "playwright", "playwright.async_api",
        "openai", "httpx",
        "yaml", "apscheduler", "loguru",
        "pydantic",
        "cryptography",
        "PyQt6", "PyQt6.QtWebEngineWidgets", "PyQt6.QtWebEngineCore",
        "PyQt6.QtWebChannel", "PyQt6.QtCharts",
        "unidecode", "slugify", "mss", "numpy",
        "src.security", "src.security.rsa_verify", "src.security.license_verify",
        "src.security.safe_modify", "src.security.strings", "src.security.auth_client",
        "src.security.token_store", "src.security.trial_store", "src.security.integrity",
        "src.security.device_fingerprint",
    ]

    datas = [
        ("os.path.join(SPECPATH, 'config')", "'config'"),
        ("os.path.join(SPECPATH, 'data/prompts')", "'data/prompts'"),
        ("os.path.join(SPECPATH, 'data/plugins')", "'data/plugins'"),
        ("os.path.join(SPECPATH, 'data/logo')", "'data/logo'"),
    ]

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    [os.path.join(SPECPATH, 'main.py')],
    pathex=[SPECPATH, os.path.join(SPECPATH, 'src')],
    binaries=[],
    datas={datas},
    hiddenimports={hidden_imports},
    hookspath=[],
    hooksconfig={{}},
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
    console=True,
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
    upx=True,
    upx_exclude=[],
    name='7tan-editor',
)
"""

    SPEC.write_text(spec_content, encoding="utf-8")
    print(f"📄 生成 {SPEC}")


def build():
    """执行 PyInstaller 构建"""
    cmd = [
        sys.executable, "-m", "PyInstaller",
        str(SPEC),
        "--distpath", str(DIST),
        "--workpath", str(BUILD),
        "--noconfirm",
        "--clean",
    ]

    print(f"🔨 开始构建: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(ROOT))

    if result.returncode == 0:
        exe_path = DIST / "7tan-editor" / "7tan-editor.exe"
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✅ 构建成功: {exe_path} ({size_mb:.1f} MB)")
        else:
            print("⚠️ 构建完成但未找到可执行文件")
    else:
        print(f"❌ 构建失败 (exit code: {result.returncode})")
        sys.exit(1)


def main():
    """主入口"""
    import argparse
    parser = argparse.ArgumentParser(description="7坛AI小编 构建工具")
    parser.add_argument("action", choices=["build", "clean", "spec"], default="build", nargs="?",
                        help="构建操作: build(构建), clean(清理), spec(生成spec)")
    args = parser.parse_args()

    if args.action == "clean":
        clean()
    elif args.action == "spec":
        generate_spec()
    elif args.action == "build":
        generate_spec()
        build()


if __name__ == "__main__":
    main()
