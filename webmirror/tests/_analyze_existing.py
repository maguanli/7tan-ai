"""体检已有镜像：逐个任务目录统计文本文件的编码健康度。"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.encoding_utils import COMMON_HANZI  # noqa: E402

DOWNLOADS = r"D:\7tan\7tanAI\webmirror\downloads"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "analyze_result.txt")

# 真正只可能来自乱码的串（去掉 □ ■ 这类正文里合法出现的字符）
MOJI_MARKS = ["锟斤拷", "�", "\ufffd"]
TEXT_EXT = (".html", ".htm", ".css", ".js", ".json", ".txt", ".xml", ".svg")


def judge(text, min_hanzi=20):
    """返回 (是否可疑, 说明)。汉字太少就不判（如压缩过的 JS）。"""
    reasons = []
    for mk in MOJI_MARKS:
        if mk in text:
            reasons.append(f"含乱码特征串 {mk!r}")
    hanzi = [c for c in text if "\u4e00" <= c <= "\u9fff"]
    ratio = None
    if len(hanzi) >= min_hanzi:
        ratio = sum(1 for c in hanzi if c in COMMON_HANZI) / len(hanzi)
        if ratio < 0.6:
            reasons.append(f"常用字占比仅 {ratio:.0%}（汉字{len(hanzi)}个）")
    return bool(reasons), reasons, ratio, len(hanzi)


def main():
    lines = []
    for task in sorted(os.listdir(DOWNLOADS)):
        root = os.path.join(DOWNLOADS, task)
        if not os.path.isdir(root) or task == "_zips":
            continue
        n_ok = n_bad = n_nonutf8 = 0
        bad_detail = []
        declared = {}
        for base, _d, fns in os.walk(root):
            for fn in fns:
                if not fn.endswith(TEXT_EXT):
                    continue
                full = os.path.join(base, fn)
                raw = open(full, "rb").read()
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    n_nonutf8 += 1
                    bad_detail.append((os.path.relpath(full, root), "非 UTF-8 字节"))
                    continue
                m = re.search(rb"charset\s*=\s*[\"']?([\w\-]+)", raw[:2048], re.I)
                d = m.group(1).decode("ascii") if m else "(无声明)"
                declared[d] = declared.get(d, 0) + 1
                bad, reasons, _r, _h = judge(text)
                if bad:
                    n_bad += 1
                    if len(bad_detail) < 5:
                        bad_detail.append((os.path.relpath(full, root), "; ".join(reasons)))
                else:
                    n_ok += 1
        lines.append(f"=== {task}")
        lines.append(f"    正常 {n_ok} / 可疑 {n_bad} / 非UTF-8 {n_nonutf8}")
        lines.append(f"    文件内声明的字符集分布: {declared}")
        for rel, why in bad_detail:
            lines.append(f"      ! {rel}: {why}")
        lines.append("")

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("done ->", OUT)


if __name__ == "__main__":
    main()
