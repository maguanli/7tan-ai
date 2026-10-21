#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""清理旧镜像中注入的 <meta name="webmirror-source"> 标记。

早期版本的 mirror 会在每个 HTML 的 <head> 首位插入：
    <meta content="原始URL" name="webmirror-source"/>
本脚本把它剥掉，让已抓取的文件恢复成与原站一致。
只需跑一次；新版本已不再注入。

用法：
    python clean_meta.py                 # 处理默认 downloads/ 目录
    python clean_meta.py <目录>          # 处理指定目录
    python clean_meta.py <目录> --dry-run  # 只统计不修改
"""
import os
import re
import sys

# 匹配被注入的 meta（attribute 顺序无关，自闭合与否都管）
META_RE = re.compile(
    r'[ \t]*<meta\b[^>]*\bname=["\']webmirror-source["\'][^>]*/?>\s*\n?',
    re.IGNORECASE,
)
# 也匹配同行内紧邻其它标签（无换行）的情形
META_INLINE_RE = re.compile(
    r'<meta\b[^>]*\bname=["\']webmirror-source["\'][^>]*/?>',
    re.IGNORECASE,
)

HTML_EXT = {".html", ".htm", ".xhtml"}


def clean_file(path: str, dry_run: bool = False) -> bool:
    """剥离单个文件里的标记，返回是否发生改动。"""
    try:
        with open(path, "r", encoding="utf-8", errors="surrogateescape") as f:
            text = f.read()
    except Exception as e:  # noqa: BLE001
        print(f"  [跳过] {path}: {e}")
        return False

    if "webmirror-source" not in text:
        return False

    new = META_RE.sub("", text)
    if "webmirror-source" in new:          # 还有同行内残留
        new = META_INLINE_RE.sub("", new)

    if new == text:
        return False

    if dry_run:
        return True
    with open(path, "w", encoding="utf-8", errors="surrogateescape") as f:
        f.write(new)
    return True


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry_run = "--dry-run" in sys.argv
    root = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "downloads")

    if not os.path.isdir(root):
        print(f"目录不存在: {root}")
        sys.exit(1)

    total = changed = scanned = 0
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if os.path.splitext(name)[1].lower() in HTML_EXT:
                scanned += 1
                if clean_file(os.path.join(dirpath, name), dry_run):
                    changed += 1
                    total += 1
                    print(f"  {'[待清理]' if dry_run else '[已清理]'} {os.path.join(dirpath, name)}")

    mode = "（预演，未写盘）" if dry_run else ""
    print(f"\n扫描 {scanned} 个 HTML，清理 {changed} 个文件{mode}。")


if __name__ == "__main__":
    main()
