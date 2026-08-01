#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
7Tan 发布拆包工具 — P2 拆包核心

生成 3 个发布 zip：
  1. 免费包      : 7tan-editor-free-v<VER>.zip            （仅 exe + _internal）
  2. 专业完整包  : 7tan-pro-src-v<VER>-<BUILD_ID>.zip      （_build + _python + rebuild.bat + 水印）
  3. 专业增量包  : 7tan-pro-update-v<VER>-<BUILD_ID>.zip   （仅 _build + rebuild.bat + 水印）

水印格式：BUILD_ID = PRO-YYYYMMDD-HHMMSS-XXXX（每份唯一）
水印写入：_build/src/config/build_info.py（随源码包分发，并编译进用户自构建的 exe）

用法（由 build_and_sync.bat 调用，也可手动执行）:
    python templates/package_release.py \
        --uid UID-20260801-00042 \\
        --version 1.0.0 \\
        --out dist/release \\
        --free-dir dist/7tan-editor \\
        --pro-build dist/_build \\
        --pro-python dist/_python \\
        --rebuild dist/rebuild.bat \\
        --license templates/LICENSE.txt

    --uid 为空时：专业包不带水印（仅内部测试用）
"""
import argparse
import datetime
import random
import sys
import zipfile
from pathlib import Path

ZIP_LEVEL = 1  # _python 体量大且多为已压缩数据，用最快压缩级别


def gen_build_id() -> str:
    """生成唯一水印：PRO-20260801-023456-8F3A"""
    now = datetime.datetime.now()
    rand = f"{random.randint(0, 0xFFFF):04X}"
    return f"PRO-{now:%Y%m%d}-{now:%H%M%S}-{rand}"


def write_build_info(build_id: str, build_user: str, out_path: Path) -> None:
    """写入水印文件（专业包内）"""
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
    """递归打包目录，返回文件数"""
    src = Path(src_dir)
    count = 0
    for p in sorted(src.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(src)
        if any(part in exclude_dirs for part in rel.parts):
            continue
        if p.name in exclude_files:
            continue
        arc = f"{arc_root}/{rel.as_posix()}"
        zf.write(p, arc)
        count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser(description="7Tan 发布拆包工具")
    ap.add_argument("--uid", default="", help="购买者 UID（提供则专业包带水印）")
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

    # ---- 1. 免费包 ----
    if not free_dir.exists():
        print(f"[ERROR] 免费目录不存在: {free_dir}")
        return 1
    free_zip = out / f"7tan-editor-free-v{ver}.zip"
    with zipfile.ZipFile(free_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as zf:
        n = zip_dir(zf, free_dir, "7tan-editor", exclude_dirs={"__pycache__", "_source_backup"})
    print(f"[OK] 免费包  : {free_zip}  ({free_zip.stat().st_size / 1048576:.1f} MB, {n} 文件)")

    # ---- 2. 专业包水印注入 ----
    build_id = ""
    suffix = ""
    if args.uid:
        build_id = gen_build_id()
        bi_path = pro_build / "src" / "config" / "build_info.py"
        write_build_info(build_id, args.uid, bi_path)
        suffix = f"-{build_id}"
        print(f"[OK] 水印注入: BUILD_ID={build_id}  BUILD_USER={args.uid}")
    else:
        print("[WARN] 未提供 --uid，专业包不带水印（仅供内部测试）")

    # ---- 3. 专业完整包（含 _python）----
    if pro_build.exists():
        pro_zip = out / f"7tan-pro-src-v{ver}{suffix}.zip"
        with zipfile.ZipFile(pro_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as zf:
            n1 = zip_dir(zf, pro_build, "7tan-pro/_build",
                         exclude_dirs={"__pycache__", "_source_backup", ".pytest_cache"})
            n2 = 0
            if Path(args.pro_python).exists():
                n2 = zip_dir(zf, args.pro_python, "7tan-pro/_python",
                             exclude_dirs={"__pycache__", "_source_backup"})
            if Path(args.rebuild).exists():
                zf.write(args.rebuild, "7tan-pro/rebuild.bat")
            if Path(args.license).exists():
                zf.write(args.license, "7tan-pro/LICENSE.txt")
            if build_id:
                zf.writestr("7tan-pro/BUILD_INFO.txt",
                            f"BUILD_ID   : {build_id}\n"
                            f"BUILD_USER : {args.uid}\n"
                            f"授权说明   : 本源码包绑定购买者账号，禁止转售/传播/公开。\n"
                            f"            解压后双击 rebuild.bat 即可自构建 exe。\n")
        print(f"[OK] 专业完整包: {pro_zip}  ({pro_zip.stat().st_size / 1048576:.1f} MB, {n1 + n2} 文件)")

        # ---- 4. 专业增量包（仅源码）----
        upd_zip = out / f"7tan-pro-update-v{ver}{suffix}.zip"
        with zipfile.ZipFile(upd_zip, "w", zipfile.ZIP_DEFLATED, compresslevel=ZIP_LEVEL) as zf:
            n1 = zip_dir(zf, pro_build, "7tan-pro/_build",
                         exclude_dirs={"__pycache__", "_source_backup", ".pytest_cache"})
            if Path(args.rebuild).exists():
                zf.write(args.rebuild, "7tan-pro/rebuild.bat")
            if Path(args.license).exists():
                zf.write(args.license, "7tan-pro/LICENSE.txt")
            zf.writestr("7tan-pro/README-增量包.txt",
                        "增量包不含 _python（便携 Python）。\n"
                        "使用方法：解压后覆盖到已有完整包目录（保持目录结构），\n"
                        "然后双击 rebuild.bat 重新构建 exe。\n")
        print(f"[OK] 专业增量包: {upd_zip}  ({upd_zip.stat().st_size / 1048576:.1f} MB, {n1} 文件)")
    else:
        print(f"[WARN] 源码目录不存在，跳过专业包: {pro_build}")

    print("\n[DONE] 发布包已生成到:", out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
