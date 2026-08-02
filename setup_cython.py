#!/usr/bin/env python3
"""
Cython 编译脚本 — 将安全模块编译为 .pyd

用法:
    python setup_cython.py              # 编译全部 3 个文件
    python setup_cython.py --dry-run    # 预览（不实际编译）
    python setup_cython.py --clean      # 清理中间文件

编译目标:
    src/security/rsa_verify.py   → src/security/rsa_verify.pyd
    src/security/license_verify.py → src/security/license_verify.pyd
    src/security/safe_modify.py  → src/security/safe_modify.pyd

编译后:
    - .pyd 文件替换 .py 文件（.py 移动至 backups/cython_backup/）
    - 清理中间 .c 文件和 build/ 目录
"""
import os
import sys
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


# ============================================================
# 配置
# ============================================================

ROOT = Path(__file__).parent
SECURITY_DIR = ROOT / "src" / "security"
BACKUP_DIR = ROOT / "backups" / "cython_backup"

# 需要编译的文件列表（相对于 SECURITY_DIR）
TARGET_FILES = [
    "rsa_verify.py",
    "license_verify.py",
    "safe_modify.py",
    "auth_client.py",
    "integrity.py",
    "token_store.py",
    "strings.py",
    "trial_store.py",
    "sec_config.py",
]

# Cython 编译选项
COMPILER_DIRECTIVES = {
    "language_level": "3",
    "boundscheck": False,
    "wraparound": False,
}


# ============================================================
# 核心逻辑
# ============================================================

def check_cython() -> bool:
    """检查 Cython 是否已安装"""
    try:
        import Cython
        print(f"✅ Cython {Cython.__version__}")
        return True
    except ImportError:
        print("❌ Cython 未安装")
        print("   请运行: pip install cython")
        return False


def check_compiler() -> bool:
    """检查 C 编译器是否可用（Windows 需要 MSVC）"""
    try:
        from setuptools import distutils
        import distutils.msvccompiler

        # 在 Windows 上检查 MSVC
        if sys.platform == "win32":
            try:
                distutils.msvccompiler.get_build_version()
                print("✅ MSVC 编译器可用")
            except Exception:
                # 尝试使用 setuptools
                pass

        return True
    except ImportError:
        print("⚠️ setuptools 未安装，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "setuptools"])
        return True


def compile_file(py_path: Path) -> Path | None:
    """
    编译单个 .py 文件为 .pyd。

    Args:
        py_path: .py 文件路径

    Returns:
        生成的 .pyd 文件路径，失败返回 None
    """
    from Cython.Build import cythonize
    from setuptools import Extension
    from distutils.core import setup as dist_setup

    name = py_path.stem
    print(f"\n🔨 编译: {py_path.name} → {name}.pyd")

    # 创建临时目录
    build_dir = ROOT / "build" / f"cython_{name}"
    build_dir.mkdir(parents=True, exist_ok=True)

    # 保存当前工作目录
    old_cwd = os.getcwd()

    try:
        os.chdir(str(SECURITY_DIR))

        # 方法：直接用 cythonize + subprocess 调用 gcc/cl
        # 这比 setuptools 更可控
        extensions = cythonize(
            [str(py_path.name)],
            compiler_directives=COMPILER_DIRECTIVES,
            build_dir=str(build_dir),
            nthreads=os.cpu_count() or 2,
        )

        if not extensions:
            print(f"  ❌ Cythonize 失败: 无输出")
            return None

        ext = extensions[0]

        # 构建扩展
        # 使用 build_ext 命令
        from setuptools.command.build_ext import build_ext
        from setuptools.dist import Distribution

        dist = Distribution({"ext_modules": [ext]})
        cmd = build_ext(dist)
        cmd.build_lib = str(build_dir)
        cmd.build_temp = str(build_dir / "temp")
        cmd.inplace = False
        cmd.ensure_finalized()
        cmd.run()

        # 查找生成的 .pyd 文件
        pyd_files = list(build_dir.rglob(f"{name}*.pyd"))
        if not pyd_files:
            # 尝试另一种查找方式
            pyd_files = list(build_dir.rglob("*.pyd"))

        if not pyd_files:
            print(f"  ⚠️ .pyd 文件未找到，尝试手动编译...")
            # 回退方案：手动调用 Cython → gcc
            result = _fallback_compile(py_path, build_dir)
            if result:
                return result
            return None

        pyd_file = pyd_files[0]
        dest = SECURITY_DIR / pyd_file.name
        shutil.copy2(pyd_file, dest)
        print(f"  ✅ 生成: {dest.name} ({_format_size(dest)})")
        return dest

    except Exception as e:
        print(f"  ❌ 编译失败: {e}")
        # 尝试回退方案
        try:
            return _fallback_compile(py_path, build_dir)
        except Exception as e2:
            print(f"  ❌ 回退编译也失败: {e2}")
            return None
    finally:
        os.chdir(old_cwd)


def _fallback_compile(py_path: Path, build_dir: Path) -> Path | None:
    """
    回退编译方案：手动 cythonize + 调用编译器。

    在 setuptools/distutils 方案不可用时使用。
    """
    name = py_path.stem
    c_file = build_dir / f"{name}.c"

    print(f"  🔄 使用回退方案...")

    # Step 1: .py → .c
    try:
        result = subprocess.run(
            [sys.executable, "-m", "cython", "-3", "-o", str(c_file), str(py_path)],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            print(f"  ❌ Cython 转译失败: {result.stderr}")
            return None
        print(f"  ✅ .c 生成: {c_file.name}")
    except Exception as e:
        print(f"  ❌ Cython 调用失败: {e}")
        return None

    # Step 2: .c → .pyd
    # Windows: 需要找到 Python 的库和头文件路径
    import sysconfig

    python_include = sysconfig.get_paths()["include"]
    python_lib = os.path.join(sys.base_prefix, "libs")

    pyd_ext = ".pyd" if sys.platform == "win32" else ".so"
    # .pyd 文件命名: {name}.cp{version}-{platform}.pyd
    # 或者直接用 {name}.pyd（看情况）
    pyd_name = f"{name}{pyd_ext}"
    pyd_path = build_dir / pyd_name

    if sys.platform == "win32":
        # 优先尝试 gcc (MinGW-w64)
        gcc = os.environ.get("CC", "gcc")
        result = subprocess.run(
            [
                gcc, "-shared", "-O2", "-fPIC",
                f"-I{python_include}",
                str(c_file),
                "-o", str(pyd_path),
                f"-L{python_lib}", f"-lpython{sys.version_info.major}{sys.version_info.minor}",
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        if result.returncode != 0:
            print(f"  ❌ GCC 编译失败: {result.stderr[:500]}")

            # 回退尝试 MSVC
            result2 = subprocess.run(
                [
                    "cl", "/nologo", "/O2", "/LD",
                    f"/I{python_include}",
                    str(c_file),
                    "/link",
                    "/DLL",
                    f"/OUT:{pyd_path}",
                ],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result2.returncode != 0:
                print(f"  ❌ MSVC 也失败。请安装 MSVC 或 clang-cl。")
                return None
    else:
        # Linux/macOS: gcc
        result = subprocess.run(
            [
                "gcc", "-shared", "-fPIC", "-O2",
                f"-I{python_include}",
                "-o", str(pyd_path),
                str(c_file),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            print(f"  ❌ GCC 编译失败: {result.stderr[:500]}")
            return None

    dest = SECURITY_DIR / pyd_name
    shutil.copy2(pyd_path, dest)
    print(f"  ✅ 回退编译成功: {dest.name}")
    return dest


def backup_original(py_path: Path) -> None:
    """备份原始 .py 文件"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"{py_path.stem}.py.{timestamp}.bak"
    backup_path = BACKUP_DIR / backup_name

    shutil.copy2(py_path, backup_path)
    print(f"  📦 备份: {backup_name}")


def cleanup_build() -> None:
    """清理中间构建文件"""
    build_dir = ROOT / "build" / "cython_*"
    # 删除 build/ 下的 cython 子目录
    build_root = ROOT / "build"
    if build_root.exists():
        for item in build_root.iterdir():
            if item.name.startswith("cython_"):
                if item.is_dir():
                    shutil.rmtree(item)
                    print(f"  🗑️ 清理: build/{item.name}")

    # 清理 .c 文件
    for c_file in SECURITY_DIR.glob("*.c"):
        c_file.unlink()
        print(f"  🗑️ 清理: {c_file.name}")


def verify_compilation() -> bool:
    """验证编译结果：尝试导入 .pyd 模块"""
    print("\n🔍 验证编译结果...")

    # 临时添加路径
    sys.path.insert(0, str(SECURITY_DIR.parent))

    all_ok = True
    for name in ["rsa_verify", "license_verify", "safe_modify", "auth_client", "integrity", "token_store", "strings", "trial_store", "sec_config"]:
        try:
            # 清理缓存
            if name in sys.modules:
                del sys.modules[name]
            if f"security.{name}" in sys.modules:
                del sys.modules[f"security.{name}"]

            mod = __import__(f"security.{name}", fromlist=[name])
            print(f"  ✅ {name} — 导入成功")
        except Exception as e:
            print(f"  ❌ {name} — 导入失败: {e}")
            all_ok = False

    return all_ok


def _format_size(path: Path) -> str:
    """格式化文件大小"""
    size = path.stat().st_size
    for unit in ["B", "KB", "MB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


# ============================================================
# 主流程
# ============================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Cython 编译安全模块 → .pyd",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python setup_cython.py              # 编译全部
  python setup_cython.py --dry-run    # 预览
  python setup_cython.py --clean      # 仅清理
        """,
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="预览，不实际编译"
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="仅清理中间文件"
    )
    parser.add_argument(
        "--skip-backup", action="store_true",
        help="跳过备份原始文件"
    )
    parser.add_argument(
        "--keep-c", action="store_true",
        help="保留 .c 中间文件"
    )
    args = parser.parse_args()

    print("=" * 60)
    print(" 7Tan — Cython 安全模块编译器")
    print("=" * 60)

    # 仅清理
    if args.clean:
        cleanup_build()
        return

    # 检查依赖
    if not check_cython():
        sys.exit(1)
    check_compiler()

    # 预览模式
    if args.dry_run:
        print("\n📋 预览编译目标:")
        for f in TARGET_FILES:
            py_path = SECURITY_DIR / f
            if py_path.exists():
                print(f"  {f} ({_format_size(py_path)}) → {py_path.stem}.pyd")
            else:
                print(f"  ❌ {f} — 文件不存在")
        return

    # 执行编译
    print(f"\n📂 源目录: {SECURITY_DIR}")
    print(f"📂 备份目录: {BACKUP_DIR}\n")

    success_list: list[str] = []
    failed_list: list[str] = []

    for f in TARGET_FILES:
        py_path = SECURITY_DIR / f

        if not py_path.exists():
            print(f"⚠️ 跳过 {f} — 文件不存在")
            failed_list.append(f)
            continue

        # 备份
        if not args.skip_backup:
            backup_original(py_path)

        # 编译
        result = compile_file(py_path)

        if result:
            success_list.append(f)
        else:
            failed_list.append(f)

    # 清理中间文件
    if not args.keep_c:
        cleanup_build()

    # 验证
    verify_compilation()

    # 总结
    print("\n" + "=" * 60)
    print(" 📊 编译总结")
    print("=" * 60)
    print(f"  ✅ 成功: {len(success_list)} 个")
    for f in success_list:
        pyd_path = SECURITY_DIR / f.replace(".py", ".pyd")
        # 可能有多版本 .pyd，找到最新的
        pyd_files = sorted(
            SECURITY_DIR.glob(f.replace(".py", "*.pyd")),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if pyd_files:
            print(f"     {pyd_files[0].name} ({_format_size(pyd_files[0])})")
        else:
            print(f"     {f} → ?")

    if failed_list:
        print(f"  ❌ 失败: {len(failed_list)} 个")
        for f in failed_list:
            print(f"     {f}")

    print(f"\n  📦 备份位置: {BACKUP_DIR}")
    print(f"  💡 构建时 .pyd 会自动替代 .py 文件")
    print(f"  💡 .py 源文件已备份，可安全删除")

    if success_list:
        print(f"\n  ⚠️ 下一步: 删除已编译的 .py 源文件？")
        print(f"     python setup_cython.py --clean-source")


if __name__ == "__main__":
    main()
