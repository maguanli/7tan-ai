# -*- coding: utf-8 -*-
"""
更新说明洁净度检查（防回归）

背景：2026-11 两次把「7723 平台截图采集」写进更新说明，用户明确要求不要出现。
本工具把该要求固化成断言，避免人工记忆失效。

检查范围（更新说明会流出的全部落点）：
    website/updates/version.json      更新清单（客户端弹窗数据源）
    website/updates/index.html        下载页
    website/manual.html               官网说明书
    templates/7Tan使用说明书.html      发布包内说明书

用法:
    python tools/check_notes_clean.py
    python tools/check_notes_clean.py --remote     # 额外核线上

退出码: 0 全部干净 / 1 有命中
"""
from __future__ import annotations

import argparse
import io
import os
import sys

# 命中即失败的词（更新说明语境）
BLOCK_TERMS = [
    "WebP",
    "截图采集",
    "7723平台",
    "7723 平台",
    "7723游戏",
    "7723 游戏",
    "7723盒子",
]

# 「7723」单独出现：排除界面示意图里的站点标识 wapli7723
NEEDLE = "7723"
WHITELIST_PREFIX = "wapli"

LOCAL_TARGETS = [
    r"website\updates\version.json",
    r"website\updates\index.html",
    r"website\manual.html",
    r"templates\7Tan使用说明书.html",
]

REMOTE_TARGETS = [
    "https://www.7tan.com/updates/version.json",
    "https://www.7tan.com/updates/index.html",
    "https://www.7tan.com/manual.html",
]

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def scan_text(name: str, text: str) -> list[str]:
    """返回该文本里的命中列表，空列表表示干净。"""
    hits: list[str] = []
    for t in BLOCK_TERMS:
        n = text.count(t)
        if n:
            hits.append(f"禁用词「{t}」x{n}")
    # 7723 裸串（排除 wapli7723）
    idx = 0
    while True:
        pos = text.find(NEEDLE, idx)
        if pos < 0:
            break
        if text[max(0, pos - len(WHITELIST_PREFIX)):pos] != WHITELIST_PREFIX:
            line_no = text.count("\n", 0, pos) + 1
            frag = text[max(0, pos - 30):pos + 20].replace("\n", " ")
            hits.append(f"「7723」@行{line_no}: …{frag}…")
        idx = pos + len(NEEDLE)
    return hits


def check_local() -> tuple[int, int]:
    ok = bad = 0
    for rel in LOCAL_TARGETS:
        p = os.path.join(BASE, rel)
        if not os.path.exists(p):
            print(f"[MISS] {rel}")
            bad += 1
            continue
        # newline='' 保留 CRLF：否则文本模式会把 \r\n 折成 \n，与线上原文字数对不上
        text = io.open(p, encoding="utf-8", errors="ignore", newline="").read()
        hits = scan_text(rel, text)
        if hits:
            bad += 1
            print(f"[FAIL] {rel}  ({len(text)} 字)")
            for h in hits:
                print(f"        - {h}")
        else:
            ok += 1
            print(f"[OK]   {rel}  ({len(text)} 字)")
    return ok, bad


def check_remote() -> tuple[int, int]:
    try:
        import urllib.request
    except Exception as e:  # pragma: no cover
        print(f"[SKIP] remote: {e}")
        return 0, 0
    ok = bad = 0
    for url in REMOTE_TARGETS:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "7tan-check/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                text = r.read().decode("utf-8", "ignore")
        except Exception as e:
            print(f"[SKIP] {url} -> {type(e).__name__}: {e}")
            continue
        hits = scan_text(url, text)
        if hits:
            bad += 1
            print(f"[FAIL] {url}  ({len(text)} 字)")
            for h in hits:
                print(f"        - {h}")
        else:
            ok += 1
            print(f"[OK]   {url}  ({len(text)} 字)")
    return ok, bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remote", action="store_true", help="额外检查线上文件")
    args = ap.parse_args()

    print("=" * 60)
    print("更新说明洁净度检查 / update-notes cleanliness")
    print("=" * 60)
    print("[本地]")
    ok1, bad1 = check_local()
    ok2 = bad2 = 0
    if args.remote:
        print("[线上]")
        ok2, bad2 = check_remote()

    total_ok, total_bad = ok1 + ok2, bad1 + bad2
    print("-" * 60)
    print(f"PASS {total_ok} / FAIL {total_bad}")
    print("RESULT", "CLEAN" if total_bad == 0 else "DIRTY")
    return 0 if total_bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
