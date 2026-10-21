"""
修复已有镜像的编码声明（**不用重新抓取**）。

背景
----
镜像一向以 UTF-8 落盘，但旧版本没有同步改写页面里残留的编码声明
（`<meta charset="gbk">`），也没有在缺少声明时补上 utf-8，
浏览器就会按旧编码 / 本地默认(GBK) 去解析 UTF-8 字节 → 整页乱码。

本脚本就地修正声明，**不改动正文一个字节**：
  *.html / *.htm : 把 charset 声明改成 utf-8；完全没有声明就补一个
  *.css          : 把 @charset 改成 utf-8

已经被抓坏的内容（服务器谎报编码导致字节已受损）无法修复，只能重抓。

用法
----
    python repair_charset.py <镜像目录>            # 预演，只统计不修改
    python repair_charset.py <镜像目录> --apply    # 实际写入
"""
from __future__ import annotations

import os
import re
import sys

CHARSET_ATTR_RE = re.compile(r"(<meta[^>]*?charset\s*=\s*[\"']?)([\w\-]+)", re.I)
META_CHARSET_EXISTS_RE = re.compile(r"<meta[^>]+charset", re.I)
HEAD_RE = re.compile(r"<head[^>]*>", re.I)
HTML_TAG_RE = re.compile(r"<html[^>]*>", re.I)
CSS_CHARSET_RE = re.compile(r"""@charset\s+(["'])[\w\-]+\1\s*;""", re.I)

HTML_EXT = {".html", ".htm", ".xhtml"}


def fix_html(text: str) -> str:
    """把 HTML 里的字符集声明统一成 utf-8；没有就补一个。"""
    if META_CHARSET_EXISTS_RE.search(text):
        return CHARSET_ATTR_RE.sub(r"\1utf-8", text)

    meta = '<meta charset="utf-8">'
    m = HEAD_RE.search(text)
    if m:
        return text[:m.end()] + "\n" + meta + text[m.end():]
    m = HTML_TAG_RE.search(text)
    if m:
        return text[:m.end()] + "\n" + meta + text[m.end():]
    return meta + "\n" + text


def fix_css(text: str) -> str:
    if CSS_CHARSET_RE.search(text[:200]):
        return CSS_CHARSET_RE.sub('@charset "utf-8";', text, count=1)
    return text


def repair(root: str, apply: bool) -> dict:
    stat = {"扫描": 0, "已是UTF-8": 0, "待修复": 0, "已修复": 0,
            "非UTF-8跳过": 0, "失败": 0}
    for base, _dirs, files in os.walk(root):
        for fn in files:
            ext = os.path.splitext(fn)[1].lower()
            if ext not in HTML_EXT and ext != ".css":
                continue
            full = os.path.join(base, fn)
            stat["扫描"] += 1
            try:
                raw = open(full, "rb").read()
                text = raw.decode("utf-8")          # 镜像一律 UTF-8
            except (OSError, UnicodeDecodeError):
                stat["非UTF-8跳过"] += 1
                continue
            new = fix_html(text) if ext in HTML_EXT else fix_css(text)
            if new == text:
                stat["已是UTF-8"] += 1
                continue
            stat["待修复"] += 1
            if apply:
                try:
                    tmp = full + ".tmp"
                    with open(tmp, "w", encoding="utf-8", newline="") as f:
                        f.write(new)
                    os.replace(tmp, full)
                    stat["已修复"] += 1
                except OSError:
                    stat["失败"] += 1
    return stat


def main() -> int:
    args = [a for a in sys.argv[1:] if a != "--apply"]
    apply = "--apply" in sys.argv
    if not args:
        print(__doc__)
        return 2
    total = {}
    for root in args:
        if not os.path.isdir(root):
            print(f"跳过（不是目录）: {root}")
            continue
        st = repair(root, apply)
        for k, v in st.items():
            total[k] = total.get(k, 0) + v
    mode = "已写入" if apply else "预演（未修改，加 --apply 才会写入）"
    print(f"[{mode}] " + "  ".join(f"{k}={v}" for k, v in total.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
