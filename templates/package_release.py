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

商业模式：软件本体免费分发，付费插件（如爆款写作 50 元/台）收费使用。

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
    "private_key.pem",
    "*.key",
    "*.p12",
    "*.pfx",
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


def main() -> int:
    ap = argparse.ArgumentParser(description="7Tan 发布打包工具（纯 exe 单包模式）")
    ap.add_argument("--uid", default="", help="分发渠道 UID（提供则写水印说明，用于溯源）")
    ap.add_argument("--version", default="1.0.0", help="版本号")
    ap.add_argument("--out", default="dist/release", help="输出目录")
    ap.add_argument("--free-dir", default="dist/7tan-editor", help="exe 目录（COLLECT 输出）")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    ver = args.version
    free_dir = Path(args.free_dir)

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
                        "\n"
                        "使用方式：\n"
                        "  解压后进入 7tan-editor/，双击 7tan-editor.exe 即可运行\n"
                        "  （无需安装 Python 或任何依赖，绿色免安装）\n"
                        "\n"
                        "系统要求：Windows 10/11 64 位\n"
                        "\n"
                        "功能说明：\n"
                        "  本软件基础功能免费使用；部分插件为付费增值服务\n"
                        "  （如「爆款写作」插件 50 元/台，永久授权，绑定当前设备）。\n"
                        "  付费详情见软件内「设置 → 插件市场」。\n")

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
