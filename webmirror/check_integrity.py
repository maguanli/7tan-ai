# -*- coding: utf-8 -*-
"""检查镜像目录的「本地引用完整性」。

扫描 HTML 标签属性（href/src/srcset/poster）与 CSS 内的 url()/@import，
确认每个本地引用都指向真实存在的文件；外部链接（http/https//）自动忽略。

用法：
    python check_integrity.py <任务目录>
    python check_integrity.py downloads/20261011-063405-6a6904
"""
import os
import posixpath
import re
import sys

SKIP = ("http://", "https://", "//", "data:", "javascript:", "mailto:", "tel:", "blob:")
TAG_RE = re.compile(r'(?:href|src|data-src|poster)\s*=\s*["\']([^"\']+)["\']', re.I)
SRCSET_RE = re.compile(r'srcset\s*=\s*["\']([^"\']+)["\']', re.I)
CSS_URL = re.compile(r'url\(\s*[\'"]?([^\'")]+)', re.I)
CSS_IMP = re.compile(r'@import\s+[\'"]([^\'"]+)[\'"]', re.I)


def is_local(u: str) -> bool:
    u = u.strip()
    return bool(u) and not u.startswith(SKIP) and not u.startswith("#")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    root = sys.argv[1]
    if not os.path.isdir(root):
        print("目录不存在:", root)
        return 1

    total = 0
    misses: list[tuple[str, str]] = []
    for r, _d, fs in os.walk(root):
        for f in fs:
            full = os.path.join(r, f)
            rel = os.path.relpath(full, root).replace("\\", "/")
            cur_dir = posixpath.dirname(rel)
            low = f.lower()
            try:
                txt = open(full, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            refs: list[str] = []
            if low.endswith((".html", ".htm", ".shtml", ".xhtml")):
                refs += TAG_RE.findall(txt)
                for ss in SRCSET_RE.findall(txt):
                    refs += [p.strip().split()[0] for p in ss.split(",") if p.strip()]
            elif low.endswith(".css"):
                refs += CSS_URL.findall(txt)
                refs += CSS_IMP.findall(txt)
            for ref in refs:
                if not is_local(ref):
                    continue
                total += 1
                tgt = posixpath.normpath(posixpath.join(cur_dir, ref.split("#")[0].split("?")[0]))
                if not os.path.isfile(os.path.join(root, *tgt.split("/"))):
                    misses.append((rel, ref))

    print(f"目录       : {root}")
    print(f"本地引用   : {total}")
    print(f"缺失引用   : {len(misses)}")
    for rel, ref in misses[:60]:
        print(f"   [缺] {ref}\n        在 {rel}")
    if len(misses) > 60:
        print(f"   … 其余 {len(misses) - 60} 条省略")
    return 0


if __name__ == "__main__":
    sys.exit(main())
