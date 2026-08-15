#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7Tan 发布打包工具 — 纯 exe 单包模式（2026-08-07 v3）

生成 1 个完整版发布 zip（免安装，双击即用）：
    7tan-editor-v<VER>[-<BUILD_ID>].zip

包内结构：
    7tan-editor/            exe + _internal（全部功能，免安装直接运行）
    BUILD_INFO.txt          构建水印（--uid 提供时写入，用于分发溯源）
    README.txt              使用说明

商业模式：软件本体免费，核心功能全部开放；个别高级插件需付费解锁。

敏感数据剔除（P1-7 规则保留）：
  - 剔除 .encryption_key、games.db*、auth/、memory/ 等开发者本地数据

v3 健壮性增强（修复 --no-build 偶发失败）：
  - 原子写入：先写 .tmp 临时包，成功后 os.replace 覆盖目标
    （不再依赖 bat 预先 del，避免"旧包被占用 → 覆盖失败"）
  - 单文件写入重试：遇杀软/进程瞬态锁自动等待重试
  - 明确错误码：0=成功 1=业务失败 2=文件被占用/IO（提示杀软白名单）

用法（由 build_and_sync.bat 调用，也可手动执行）:
    python templates/package_release.py \
        --uid UID-20260801-00042 \
        --version 1.0.6 \
        --out dist/release \
        --free-dir dist/7tan-editor

    --uid 为空时：不带水印（仅内部测试用）
"""
import argparse
import datetime
import fnmatch
import os
import random
import sys
import time
import zipfile
from pathlib import Path

ZIP_LEVEL = 6        # 纯 exe 包，用默认压缩级别平衡体积与速度
WRITE_RETRY = 3      # 单文件写入失败重试次数（杀软瞬态锁）
WRITE_RETRY_DELAY = 0.5
REPLACE_RETRY = 12   # 最终替换目标失败重试次数（杀软扫描 300MB+ zip 可达十几秒）
REPLACE_RETRY_DELAY = 2.0

# ============================================================
# P1-7 敏感数据黑名单（开发者本地数据，绝不能进发布包）
# ============================================================

# 目录名黑名单：路径中任意一级目录名命中即跳过
#   auth/       — 登录烙印记（用户名+指纹）
#   memory/     — 本地记忆库
#   sandbox/    — 沙盒调试文件
#   screenshots/ video_editor/ web_cache/ — 运行时缓存
EXCLUDE_DIRS = {
    "__pycache__",
    "_source_backup",
    ".pytest_cache",
    "auth",
    "memory",
    "sandbox",
    "screenshots",
    "video_editor",
    "web_cache",
}

# 文件名黑名单（支持 fnmatch 通配符）
#   .encryption_key / .encryption_salt — 本地加密密钥（首次运行自动生成）
#   *.db* — 开发者本地数据库（games.db / 7tan.db / app.db / -wal / -shm）
#   test_*.py _fix*.py fix_*.py *.bak — 调试脚本/旧版备份
#   *_result.txt 等 — 调试输出
EXCLUDE_FILE_PATTERNS = {
    ".encryption_key",
    ".encryption_salt",
    ".env",
    ".env.*",
    "private_key.pem",
    "*.key",
    "*.p12",
    "*.pfx",
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.bak",
    "*.broken_*",
    "*.tmp",
    "test_*.py",
    "_check_*.py",
    "_fix_*.py",
    "fix_*.py",
    "stats_models.py",
    "cap_func.txt",
    "db_func*.txt",
    "db_summary.txt",
    "capabilities_verify.txt",
    "*_result.txt",
    "hl_*.txt",
    "sw_*.txt",
    "costs.json",
    "state.json",
    "url_history.txt",
    "device_last_report.json",
}


def gen_build_id() -> str:
    """生成唯一水印：PRO-20260801-023456-8F3A"""
    now = datetime.datetime.now()
    rand = f"{random.randint(0, 0xFFFF):04X}"
    return f"PRO-{now:%Y%m%d}-{now:%H%M%S}-{rand}"


def _safe_write(zf: zipfile.ZipFile, src: Path, arc: str) -> None:
    """写入单个文件，遇瞬态锁（杀软扫描等）自动重试，避免偶发 PermissionError"""
    last_err = None
    for i in range(WRITE_RETRY + 1):
        try:
            zf.write(src, arc)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            if i < WRITE_RETRY:
                time.sleep(WRITE_RETRY_DELAY)
    raise last_err


def zip_dir(zf: zipfile.ZipFile, src_dir, arc_root: str,
            exclude_dirs=(), exclude_files=()) -> int:
    """递归打包目录，返回文件数

    exclude_dirs  : 目录名黑名单（路径任意段命中即跳过）
    exclude_files : 文件名黑名单（支持 fnmatch 通配符）
    """
    src = Path(src_dir)
    count = 0
    skipped = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        if any(part in exclude_dirs for part in rel.parts):
            skipped += 1
            continue
        if any(fnmatch.fnmatch(p.name, pat) for pat in exclude_files):
            skipped += 1
            continue
        arc = f"{arc_root}/{rel.as_posix()}"
        _safe_write(zf, p, arc)
        count += 1
    if skipped:
        print(f"    (已剔除 {skipped} 个敏感/调试文件)")
    return count


def _atomic_replace(tmp: Path, dst: Path) -> None:
    """原子替换目标。目标被占用（杀软扫描/资源管理器）时等待重试。

    策略：
      1. 先探测目标锁（可写则锁已释放），避免无谓等待
      2. os.replace 失败按 REPLACE_RETRY×DELAY 重试（最长约 24s，覆盖杀软大文件扫描）
      3. 兜底：若目标允许删除，走「先删后改」双保险
    """
    last_err = None
    for i in range(REPLACE_RETRY + 1):
        # 探测目标锁：能打开说明扫描/占用已结束
        if dst.exists():
            try:
                with open(dst, "r+b"):
                    pass
            except PermissionError:
                last_err = PermissionError(f"目标文件被占用: {dst}")
                time.sleep(REPLACE_RETRY_DELAY)
                continue
        try:
            os.replace(tmp, dst)
            return
        except (PermissionError, OSError) as e:
            last_err = e
            if i < REPLACE_RETRY:
                time.sleep(REPLACE_RETRY_DELAY)
    # 兜底：目标允许删除时，先删后改（应对「禁替换但允许删除」的锁）
    try:
        if dst.exists():
            dst.unlink()
        os.replace(tmp, dst)
        return
    except (PermissionError, OSError):
        raise last_err


def _safe_cleanup(path: Path) -> None:
    """尽力清理临时文件（失败忽略）"""
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass


# ============================================================
# 源码构建工具链打包（7tan-src/）
# 完整版 = exe（免安装运行） + 源码（可自行构建打包）
# ============================================================

# 显式文件清单：(项目内相对路径, zip 内路径)
_SOURCE_FILES = [
    ("main.py",                      "7tan-src/main.py"),
    ("build.spec",                   "7tan-src/build.spec"),
    ("build.bat",                    "7tan-src/build.bat"),
    ("requirements.txt",             "7tan-src/requirements.txt"),
    ("setup_cython.py",              "7tan-src/setup_cython.py"),
    ("data/__init__.py",             "7tan-src/data/__init__.py"),
    ("tools/gen_plugin_hashes.py",   "7tan-src/tools/gen_plugin_hashes.py"),
    ("templates/README_BUILD.md",    "7tan-src/README_BUILD.md"),
    ("templates/setup.bat",          "7tan-src/setup.bat"),
]

# 目录清单：(项目内相对路径, zip 内路径)
_SOURCE_DIRS = [
    ("src",                "7tan-src/src"),
    ("config",             "7tan-src/config"),
    ("data/plugins",       "7tan-src/data/plugins"),
    ("data/logo",          "7tan-src/data/logo"),
    ("tools/security_src", "7tan-src/tools/security_src"),
]

# 源码包额外排除（构建产物/运行数据/仓库杂物）
_SOURCE_EXCLUDE_DIRS = EXCLUDE_DIRS | {
    "__pycache__", ".venv", ".git", ".pytest_cache",
    "dist", "build", "logs", "downloads", "output", "recordings",
    "backups", "temp", "tmp", "designs", "article_images",
    "extensions", "mini_rts", "server", "website", "www",
    "vscode-extension", "scripts", "tests", "docs",
    "browser_profile", "prompts", "users",
}


def add_source_bundle(zf: zipfile.ZipFile, project_root) -> int:
    """把完整源码 + 构建工具链写入 zip 的 7tan-src/ 目录（仅构建 exe，不提供打包脚本）。

    只打包构建必需内容（main.py/src/config/data/plugins/data/logo/tools/security_src
    + build.spec/build.bat/requirements.txt/
    README_BUILD.md/setup.bat），绝不包含 .venv/dist/build/data 运行数据等。
    """
    root = Path(project_root)
    count = 0
    for rel, arc in _SOURCE_FILES:
        src = root / rel
        if not src.exists():
            print(f"  [WARN] 源码包缺少文件（跳过）: {rel}")
            continue
        _safe_write(zf, src, arc)
        count += 1
    for rel, arc in _SOURCE_DIRS:
        src = root / rel
        if not src.exists():
            print(f"  [WARN] 源码包缺少目录（跳过）: {rel}")
            continue
        n = zip_dir(zf, src, arc,
                    exclude_dirs=_SOURCE_EXCLUDE_DIRS,
                    exclude_files=EXCLUDE_FILE_PATTERNS)
        count += n
    return count


# ============================================================
# 其他系统通用包（WEB 版，macOS / Linux / 鸿蒙 等非 Windows 系统）
# 不含 exe：解压后双击对应平台启动脚本 → 自动装依赖 → WEB 版直接可用
# ============================================================

# WEB 版根目录文件清单：(项目内相对路径, zip 内路径)
_WEB_ROOT_FILES = [
    ("web_main.py",                     "web_main.py"),
    ("main.py",                         "main.py"),
    ("requirements-web.txt",            "requirements-web.txt"),
    ("启动网页版服务(macOS).command",    "启动网页版服务(macOS).command"),
    ("启动网页版服务(Linux).sh",        "启动网页版服务(Linux).sh"),
]

# WEB 版目录清单：(项目内相对路径, zip 内路径, 额外排除目录名)
_WEB_DIRS = [
    ("src",           "src",           {"ui", "__pycache__"}),
    ("config",        "config",        set()),
    ("data/plugins",  "data/plugins",  {"backup", "__pycache__"}),
    ("data/logo",     "data/logo",     set()),
    ("tools",         "tools",         {"__pycache__"}),
]

# WEB 版额外排除文件（PyQt6 桌面专用，避免非 Windows 依赖报错）
_WEB_EXCLUDE_FILES = EXCLUDE_FILE_PATTERNS | {
    "browser_bridge.py",
    "cookie_manager.py",
    "*.pyc",
}

_WEB_README = (
    "7Tan WEB 版（其他操作系统通用包）\n"
    "====================================\n"
    "适用系统：macOS / Linux / 鸿蒙 PC 等非 Windows 系统\n"
    "（Windows 用户请下载 Windows 专属完整包）\n"
    "\n"
    "快速开始：\n"
    "  1. 解压本 ZIP 到任意目录（路径建议不要含中文）\n"
    "  2. 选择对应系统的启动脚本：\n"
    "       macOS   → 双击「启动网页版服务(macOS).command」\n"
    "                 （首次提示权限，请右键→打开）\n"
    "       Linux   → 终端执行：bash 启动网页版服务(Linux).sh\n"
    "  3. 脚本自动检查/安装依赖，并启动 http://127.0.0.1:9900/\n"
    "  4. 浏览器打开 WEB 版后，按页面提示点击【确认适配】，\n"
    "     7Tan 自动完成当前系统的插件复制适配，全部功能可用\n"
    "\n"
    "系统要求：Python 3.10+（脚本会自动提示安装方法）\n"
    "\n"
    "功能说明：\n"
    "  - 完整 WEB 版：对话 / 编程 / 爬虫 / 写作 / 代码工具 / 记忆 / 统计等\n"
    "  - Windows 专属插件（桌面控制、公众号发布）在非 Windows 系统\n"
    "    自动适配或友好降级\n"
    "  - 详细说明见《7Tan使用说明书.html》\n"
)


def build_web_only_zip(out: Path, ver: str, uid: str, project_root) -> int:
    """打包「其他系统通用包」：WEB 版源码 + 启动脚本 + 跨平台插件 + 平台适配器。

    不含 exe / 桌面 UI（src/ui、PyQt6 专属文件），解压即用。
    """
    root = Path(project_root)
    build_id = ""
    suffix = ""
    if uid:
        build_id = gen_build_id()
        suffix = f"-{build_id}"

    zip_name = f"7tan-web-v{ver}{suffix}.zip"
    all_zip = out / zip_name
    tmp_zip = out / f".{zip_name}.{os.getpid()}.tmp"
    n_total = 0
    try:
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as zf:
            # 1. 根目录文件（启动脚本 / 入口 / 依赖清单）
            for rel, arc in _WEB_ROOT_FILES:
                src = root / rel
                if not src.exists():
                    print(f"  [WARN] 缺少文件（跳过）: {rel}")
                    continue
                _safe_write(zf, src, arc)
                n_total += 1
                print(f"  [OK] {arc} ({src.stat().st_size:,}B)")
            # 2. 目录（src 排除桌面 ui；plugins 保留 variants 排除 backup）
            for rel, arc, extra_dirs in _WEB_DIRS:
                src = root / rel
                if not src.exists():
                    print(f"  [WARN] 缺少目录（跳过）: {rel}")
                    continue
                n = zip_dir(zf, src, arc,
                            exclude_dirs=EXCLUDE_DIRS | extra_dirs,
                            exclude_files=_WEB_EXCLUDE_FILES)
                print(f"  [OK] {arc}/  {n} 文件")
                n_total += n
            # 3. 水印
            if build_id:
                zf.writestr("BUILD_INFO.txt",
                            f"BUILD_ID   : {build_id}\n"
                            f"渠道       : {uid}\n"
                            f"说明       : 本文件用于分发溯源，请勿删除。\n")
            # 4. 使用说明
            zf.writestr("README_WEB.txt", _WEB_README)
            # 5. 说明书
            for _doc_name in ["7Tan使用说明书.md", "7Tan使用说明书.html"]:
                _doc_src = root / "templates" / _doc_name
                if _doc_src.exists():
                    _safe_write(zf, _doc_src, _doc_name)
                    print(f"  [OK] {_doc_name} ({_doc_src.stat().st_size:,}B)")

        _atomic_replace(tmp_zip, all_zip)
    except PermissionError as e:
        print(f"[ERROR] 发布包写入失败：文件被占用或杀毒软件正在扫描（{e}）")
        print("        请关闭 dist\\release 下已打开的 zip，或将 dist 目录加入杀软白名单后重试。")
        _safe_cleanup(tmp_zip)
        return 2
    except OSError as e:
        print(f"[ERROR] 发布包写入失败：{e}")
        print("        请检查磁盘空间与目录权限。")
        _safe_cleanup(tmp_zip)
        return 2
    except Exception as e:
        print(f"[ERROR] 打包失败：{type(e).__name__}: {e}")
        _safe_cleanup(tmp_zip)
        return 1

    size_mb = all_zip.stat().st_size / 1048576
    print(f"\n[OK] 其他系统通用包: {all_zip}  ({size_mb:.1f} MB, {n_total} 文件)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="7Tan 发布打包工具（纯 exe 单包 / 其他系统通用包）")
    ap.add_argument("--uid", default="", help="分发渠道 UID（提供则写水印说明，用于溯源）")
    ap.add_argument("--version", default="1.0.0", help="版本号")
    ap.add_argument("--out", default="dist/release", help="输出目录")
    ap.add_argument("--free-dir", default="dist/7tan-editor", help="exe 目录（COLLECT 输出）")
    ap.add_argument("--web-only", action="store_true",
                    help="只打包「其他系统通用包」（WEB 版，不含 exe，macOS/Linux/鸿蒙用）")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ver = args.version
    free_dir = Path(args.free_dir)

    # ---- 0.5 其他系统通用包模式（不含 exe，WEB 版）----
    if args.web_only:
        return build_web_only_zip(out, ver, args.uid, Path(__file__).resolve().parent.parent)

    # ---- 0. 基础检查 ----
    if not free_dir.exists():
        print(f"[ERROR] exe 目录不存在: {free_dir}")
        return 1
    exe_file = free_dir / "7tan-editor.exe"
    if not exe_file.exists():
        print(f"[ERROR] 未找到主程序: {exe_file}")
        return 1
    exe_size = exe_file.stat().st_size
    if exe_size < 15000000:
        print(f"[ERROR] exe 大小异常（{exe_size} 字节），构建不完整！")
        return 1
    print(f"[OK] 主程序检查通过: {exe_file} ({exe_size / 1048576:.1f} MB)")

    # ---- 1. 水印（--uid 提供时）----
    build_id = ""
    suffix = ""
    if args.uid:
        build_id = gen_build_id()
        suffix = f"-{build_id}"
        print(f"[OK] 分发水印: BUILD_ID={build_id}  渠道={args.uid}")
    else:
        print("[WARN] 未提供 --uid，不带水印（仅供内部测试）")

    # ---- 2. 纯 exe 单包（原子写入：临时包 → 校验 → 覆盖目标）----
    zip_name = f"7tan-editor-v{ver}{suffix}.zip"
    all_zip = out / zip_name
    tmp_zip = out / f".{zip_name}.{os.getpid()}.tmp"
    n_total = 0
    try:
        with zipfile.ZipFile(tmp_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as zf:
            # 2.1 exe 目录（免安装直接运行，全部功能）
            n1 = zip_dir(zf, free_dir, "7tan-editor",
                         exclude_dirs=EXCLUDE_DIRS,
                         exclude_files=EXCLUDE_FILE_PATTERNS)
            print(f"  [OK] 7tan-editor/  {n1} 文件")
            n_total += n1

            # 2.2 水印说明
            if build_id:
                zf.writestr("BUILD_INFO.txt",
                            f"BUILD_ID   : {build_id}\n"
                            f"渠道       : {args.uid}\n"
                            f"说明       : 本文件用于分发溯源，请勿删除。\n")

            # 2.3 根 README 使用说明
            zf.writestr("README.txt",
                        "7Tan 编辑器（完整版）\n"
                        "=====================\n"
                        "目录结构：\n"
                        "  7tan-editor/    免安装版，双击 7tan-editor.exe 即可运行\n"
                        "  7tan-src/       完整源码 + 构建工具链（可自行构建 exe）\n"
                        "\n"
                        "使用方式：\n"
                        "  解压后进入 7tan-editor/，双击 7tan-editor.exe 即可运行\n"
                        "  （无需安装 Python 或任何依赖，绿色免安装）\n"
                        "\n"
                        "自行构建：\n"
                        "  进入 7tan-src/，按 README_BUILD.md 说明操作：\n"
                        "    setup.bat                一键准备构建环境\n"
                        "    build.bat                构建 exe（仅构建，不含打包）\n"
                        "\n"
                        "授权声明：\n"
                        "  本软件版权归开发者所有，源码与构建产物仅限个人使用，\n"
                        "  禁止打包再分发、转售或用于任何商业用途。\n"
                        "\n"
                        "系统要求：Windows 10/11 64 位\n"
                        "\n"
                        "功能说明：\n"
                        "  本软件本体免费，核心功能全部开放使用；\n  个别高级插件（如爆款写作等）需付费解锁。\n"
                        "  详细使用说明见《7Tan使用说明书.md / .html》。\n")

            # 2.3.1 使用说明书（完全免费版随包附带）
            for _doc_name in ["7Tan使用说明书.md", "7Tan使用说明书.html"]:
                _doc_src = Path(__file__).resolve().parent.parent / "templates" / _doc_name
                if _doc_src.exists():
                    _safe_write(zf, _doc_src, _doc_name)
                    print(f"  [OK] {_doc_name} ({_doc_src.stat().st_size:,}B)")

            # 2.3.2 绿色版一键启动脚本（ZIP 根目录，按操作系统选择对应文件双击/执行：自启+启动服务+开浏览器）
            # Windows 专属完整包：仅内置 Windows 启动脚本（macOS/Linux 脚本只在通用包里）
            _launchers = [
                ("启动网页版服务(Windows).bat", "Windows"),
            ]
            for _launcher_name, _os_name in _launchers:
                _launcher_src = Path(__file__).resolve().parent.parent / _launcher_name
                if _launcher_src.exists():
                    _safe_write(zf, _launcher_src, _launcher_name)
                    print(f"  [OK] {_launcher_name} ({_launcher_src.stat().st_size:,}B)")
                else:
                    print(f"  [WARN] {_launcher_name} 不存在，已跳过（{_os_name} 用户将无一键启动）")

            # 2.4 完整源码 + 构建工具链（7tan-src/，让"完整版"可自行构建）
            n_src = add_source_bundle(zf, Path(__file__).resolve().parent.parent)
            print(f"  [OK] 7tan-src/  {n_src} 文件")
            n_total += n_src

        # 临时包写完后，原子替换目标（旧包被占用也能覆盖；实在占用则重试）
        _atomic_replace(tmp_zip, all_zip)
    except PermissionError as e:
        print(f"[ERROR] 发布包写入失败：文件被占用或杀毒软件正在扫描（{e}）")
        print("        请关闭 dist\\release 下已打开的 zip，或将 dist 目录加入杀软白名单后重试。")
        _safe_cleanup(tmp_zip)
        return 2
    except OSError as e:
        print(f"[ERROR] 发布包写入失败：{e}")
        print("        请检查磁盘空间与目录权限。")
        _safe_cleanup(tmp_zip)
        return 2
    except Exception as e:
        print(f"[ERROR] 打包失败：{type(e).__name__}: {e}")
        _safe_cleanup(tmp_zip)
        return 1

    size_mb = all_zip.stat().st_size / 1048576
    print(f"\n[OK] 发布包: {all_zip}  ({size_mb:.1f} MB, {n_total} 文件)")

    print("\n[DONE] 发布包已生成到:", out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
