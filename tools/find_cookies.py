# -*- coding: utf-8 -*-
"""搜索 QtWebEngine / Chromium 系 Cookies 数据库文件"""
import os
from pathlib import Path

def find_cookies(roots):
    found = []
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            # 跳过太大的目录
            try:
                if any(skip in dirpath.lower() for skip in ['cache', 'code cache', 'gpucache', 'shader']):
                    continue
                for fn in filenames:
                    if fn.lower() in ('cookies', 'cookies.sqlite', 'cookies.db'):
                        p = Path(dirpath) / fn
                        try:
                            size = p.stat().st_size
                            if size > 1024:
                                found.append((str(p), size))
                        except OSError:
                            pass
            except PermissionError:
                continue
            if len(found) >= 30:
                return found
    return found

import sys
sys.stdout.reconfigure(encoding='utf-8')

roots = [
    os.environ.get('LOCALAPPDATA', r'C:\Users\%s\AppData\Local' % os.environ.get('USERNAME', '')),
    os.environ.get('APPDATA', r'C:\Users\%s\AppData\Roaming' % os.environ.get('USERNAME', '')),
    r'D:\7tan\7tanAI\data',
]
print("搜索根目录:", roots)
found = find_cookies(roots)
if found:
    print(f"\n找到 {len(found)} 个 Cookies 文件:")
    for p, size in found:
        print(f"  {p}  ({size/1024:.1f} KB)")
else:
    print("未找到 Cookies 文件")
