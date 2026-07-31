# -*- coding: utf-8 -*-
import os

internal = r"D:\7tan\7tanAI\dist\7tan-editor\_internal"
print("=== _internal 全部文件 ===")
for f in sorted(os.listdir(internal)):
    full = os.path.join(internal, f)
    tag = "DIR" if os.path.isdir(full) else "%dB" % os.path.getsize(full)
    mark = "  <<< 关键" if (f.lower().endswith(".pyz") or "base_library" in f.lower()) else ""
    print("  ", f, tag, mark)

print("\n=== PYZ.pyz 是否存在 ===")
pyz = os.path.join(internal, "PYZ.pyz")
print("存在!" if os.path.exists(pyz) else "【不存在!】← 这就是找不到模块的原因")
