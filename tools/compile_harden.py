#!/usr/bin/env python3
"""
通用 Cython 编译脚本 — 将高价值明文模块编译为 .pyd

用法:
    python tools/compile_harden.py              # 编译全部 3 个
    python tools/compile_harden.py --dry-run    # 预览
"""
import io
import os
import shutil
import subprocess
import sys
import sysconfig
from datetime import datetime
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
BACKUP_DIR = ROOT / "backups" / "cython_backup"

# (源文件, 目标目录) —— 编译后 .pyd 覆盖同目录 .py，.py 移入备份
TARGETS = [
    (ROOT / "src" / "security" / "device_fingerprint.py", ROOT / "src" / "security"),
    (ROOT / "src" / "core" / "updater.py", ROOT / "src" / "core"),
    (ROOT / "src" / "agent" / "prompts.py", ROOT / "src" / "agent"),
    # 插件完整性守卫（P1-1: 插件 SHA-256 白名单 + HMAC 签名）
    (ROOT / "src" / "security" / "plugin_guard.py", ROOT / "src" / "security"),
]

COMPILER_DIRECTIVES = {
    "language_level": "3",
    "boundscheck": False,
    "wraparound": False,
}


def cythonize_to_c(py_path: Path, out_dir: Path) -> Path | None:
    """py → .c"""
    c_file = out_dir / f"{py_path.stem}.c"
    result = subprocess.run(
        [sys.executable, "-m", "cython", "-3", "-o", str(c_file), str(py_path)],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode != 0:
        print(f"  ❌ Cython 转译失败: {result.stderr[:500]}")
        return None
    return c_file


def compile_c_to_pyd(c_file: Path, out_dir: Path, name: str) -> Path | None:
    """.c → .pyd（优先 gcc，回退 MSVC）"""
    python_include = sysconfig.get_paths()["include"]
    python_lib = os.path.join(sys.base_prefix, "libs")
    pyd_path = out_dir / f"{name}.pyd"

    gcc = os.environ.get("CC", "gcc")
    result = subprocess.run(
        [
            gcc, "-shared", "-O2", "-fPIC",
            f"-I{python_include}",
            str(c_file),
            "-o", str(pyd_path),
            f"-L{python_lib}", f"-lpython{sys.version_info.major}{sys.version_info.minor}",
        ],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode == 0:
        return pyd_path

    print(f"  ⚠️ GCC 失败，尝试 MSVC: {result.stderr[:300]}")
    result2 = subprocess.run(
        ["cl", "/nologo", "/O2", "/LD",
         f"/I{python_include}", str(c_file),
         "/link", "/DLL", f"/OUT:{pyd_path}"],
        capture_output=True, text=True, timeout=180,
    )
    if result2.returncode == 0:
        return pyd_path
    print(f"  ❌ MSVC 也失败: {result2.stderr[:300]}")
    return None


def main():
    dry = "--dry-run" in sys.argv
    print("=" * 60)
    print(" 7Tan — Cython 扩展编译 (P0 加固)")
    print("=" * 60)

    for py_path, out_dir in TARGETS:
        name = py_path.stem
        pyd_target = out_dir / f"{name}.pyd"
        if dry:
            print(f"  [预览] {py_path.name} → {pyd_target.name}")
            continue

        if not py_path.exists():
            print(f"⚠️ 跳过 {py_path} — 文件不存在")
            continue
        if pyd_target.exists():
            print(f"⏭️ 跳过 {name} — 已存在 {pyd_target.name}（如需重编请先删除）")
            continue

        print(f"\n🔨 编译: {py_path.name}")

        # 1. 备份源码
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(py_path, BACKUP_DIR / f"{name}.py.{ts}.bak")
        print(f"  📦 备份: {name}.py.{ts}.bak")

        # 2. py → c
        c_file = cythonize_to_c(py_path, out_dir)
        if not c_file:
            continue

        # 3. c → pyd
        pyd = compile_c_to_pyd(c_file, out_dir, name)
        if not pyd:
            continue

        # 4. 清理 .c，删除 .py（已被备份）
        c_file.unlink(missing_ok=True)
        py_path.unlink(missing_ok=True)
        print(f"  ✅ 编译成功: {pyd.name} ({pyd.stat().st_size/1024:.1f} KB)，源码已备份")

    print("\n✅ 完成")


if __name__ == "__main__":
    main()
