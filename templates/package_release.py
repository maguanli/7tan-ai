#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7Tan 发布打包工具 — 单包模式（2026-08-07 重构，替代原 3 包拆包）

生成 1 个全量发布 zip（免费版 exe + 专业版源码合体）：
    7tan-all-v<VER>[-<BUILD_ID>].zip

包内结构：
    7tan-editor/            exe + _internal（免安装，双击直接运行）
    7tan-pro/_build         完整源码（可用 rebuild.bat 自构建）
    7tan-pro/_python        便携 Python 环境（自构建所需）
    7tan-pro/rebuild.bat    一键重建脚本
    7tan-pro/LICENSE.txt    授权协议
    7tan-pro/BUILD_INFO.txt 构建水印（--uid 提供时写入，用于泄露溯源）
    README.txt              使用说明

水印格式：BUILD_ID = PRO-YYYYMMDD-HHMMSS-XXXX（每份唯一）
水印写入：_build/src/config/build_info.py（随源码分发，并编译进用户自构建的 exe）

敏感数据剔除（P1-7 规则保留）：
  - 剔除 .encryption_key、games.db*、auth/、memory/ 等开发者本地数据
  - 保留 logo/ prompts/ plugins/（build.spec 引用，剔除会导致买家自构建失败）

用法（由 build_and_sync.bat 调用，也可手动执行）:
    python templates/package_release.py \
        --uid UID-20260801-00042 \
        --version 1.0.0 \
        --out dist/release \
        --free-dir dist/7tan-editor \
        --pro-build dist/_build \
        --pro-python dist/_python \
        --rebuild dist/rebuild.bat \
        --license templates/LICENSE.txt

    --uid 为空时：不带水印（仅内部测试用）
"""
import argparse
import datetime
import fnmatch
import random
import sys
import zipfile
from pathlib import Path

ZIP_LEVEL = 1  # _python 体量大且多为已压缩数据，用最快压缩级别

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
    "*.db",
    "*.db-wal",
    "*.db-shm",
    "*.bak",
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


def write_build_info(build_id: str, build_user: str, out_path: Path) -> None:
    """写入水印文件（专业源码内）"""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = (
        '"""\n'
        "构建水印 — 由 package_release.py 自动生成，请勿手改\n"
        "BUILD_ID 用于泄露溯源，绑定购买者账号，禁止转售/传播\n"
        '"""\n'
        f'BUILD_ID = "{build_id}"\n'
        f'BUILD_TIME = "{now}"\n'
        f'BUILD_USER = "{build_user}"\n'
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")
    print(f"  [水印] {build_id} -> {out_path}")


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
        zf.write(p, arc)
        count += 1
    if skipped:
        print(f"    (已剔除 {skipped} 个敏感/调试文件)")
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="7Tan 发布打包工具（单包模式）")
    ap.add_argument("--uid", default="", help="购买者 UID（提供则带水印）")
    ap.add_argument("--version", default="1.0.0", help="版本号")
    ap.add_argument("--out", default="dist/release", help="输出目录")
    ap.add_argument("--free-dir", default="dist/7tan-editor", help="免费版 exe 目录")
    ap.add_argument("--pro-build", default="dist/_build", help="专业版源码目录")
    ap.add_argument("--pro-python", default="dist/_python", help="便携 Python 目录")
    ap.add_argument("--rebuild", default="dist/rebuild.bat", help="rebuild.bat 路径")
    ap.add_argument("--license", default="templates/LICENSE.txt", help="授权协议文件")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ver = args.version
    free_dir = Path(args.free_dir)
    pro_build = Path(args.pro_build)
    pro_python = Path(args.pro_python)

    # ---- 0. 基础检查 ----
    if not free_dir.exists():
        print(f"[ERROR] exe 目录不存在: {free_dir}")
        return 1

    # ---- 1. 水印注入（--uid 提供时）----
    build_id = ""
    suffix = ""
    if args.uid:
        build_id = gen_build_id()
        bi_path = pro_build / "src" / "config" / "build_info.py"
        write_build_info(build_id, args.uid, bi_path)
        suffix = f"-{build_id}"
        print(f"[OK] 水印注入: BUILD_ID={build_id}  BUILD_USER={args.uid}")
    else:
        print("[WARN] 未提供 --uid，不带水印（仅供内部测试）")

    # ---- 2. 单全量包 ----
    all_zip = out / f"7tan-all-v{ver}{suffix}.zip"
    n_total = 0
    with zipfile.ZipFile(all_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as zf:
        # 2.1 exe 目录（免安装直接运行）
        n1 = zip_dir(zf, free_dir, "7tan-editor",
                     exclude_dirs=EXCLUDE_DIRS,
                     exclude_files=EXCLUDE_FILE_PATTERNS)
        print(f"  [OK] 7tan-editor/  {n1} 文件")
        n_total += n1

        # 2.2 专业源码
        if pro_build.exists():
            n2 = zip_dir(zf, pro_build, "7tan-pro/_build",
                         exclude_dirs=EXCLUDE_DIRS,
                         exclude_files=EXCLUDE_FILE_PATTERNS)
            print(f"  [OK] 7tan-pro/_build  {n2} 文件")
            n_total += n2
        else:
            print(f"  [WARN] 源码目录不存在，跳过: {pro_build}")

        # 2.3 便携 Python（自构建环境）
        if pro_python.exists():
            n3 = zip_dir(zf, pro_python, "7tan-pro/_python",
                         exclude_dirs={"__pycache__", "_source_backup"},
                         exclude_files=())
            print(f"  [OK] 7tan-pro/_python  {n3} 文件")
            n_total += n3
        else:
            print(f"  [WARN] 便携 Python 不存在，跳过: {pro_python}")

        # 2.4 构建脚本 + 授权协议
        if Path(args.rebuild).exists():
            zf.write(args.rebuild, "7tan-pro/rebuild.bat")
        if Path(args.license).exists():
            zf.write(args.license, "7tan-pro/LICENSE.txt")

        # 2.5 水印说明
        if build_id:
            zf.writestr("7tan-pro/BUILD_INFO.txt",
                        f"BUILD_ID   : {build_id}\n"
                        f"BUILD_USER : {args.uid}\n"
                        f"授权说明   : 本源码包绑定购买者账号，禁止转售/传播/公开。\n"
                        f"            解压后双击 rebuild.bat 即可自构建 exe。\n")

        # 2.6 根 README 使用说明
        zf.writestr("README.txt",
                    "7Tan 全量包（免费版 + 专业源码）\n"
                    "================================\n"
                    "目录结构：\n"
                    "  7tan-editor/    免安装版，双击 7tan-editor.exe 即可运行\n"
                    "  7tan-pro/       专业源码 + 便携 Python + rebuild.bat\n"
                    "\n"
                    "使用方式（二选一）：\n"
                    "  A. 直接运行：进入 7tan-editor/，双击 7tan-editor.exe\n"
                    "  B. 源码自构建：进入 7tan-pro/，双击 rebuild.bat\n"
                    "\n"
                    "系统要求：Windows 10/11 64 位\n"
                    "授权说明：详见 7tan-pro/LICENSE.txt；源码绑定购买者账号，禁止转售/传播。\n")

    size_mb = all_zip.stat().st_size / 1048576
    print(f"\n[OK] 全量包: {all_zip}  ({size_mb:.1f} MB, {n_total} 文件)")

    print("\n[DONE] 发布包已生成到:", out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
