# -*- coding: utf-8 -*-
import os

root = r"D:\7tan\7tanAI\dist\7tan-editor"
out = []
out.append("=== dist\\7tan-editor ===")
for f in sorted(os.listdir(root)):
    full = os.path.join(root, f)
    out.append("  %s %s %s" % ("DIR" if os.path.isdir(full) else "FILE", f,
                                "" if os.path.isdir(full) else os.path.getsize(full)))

internal = os.path.join(root, "_internal")
out.append("\n=== _internal (共 %d 项) ===" % len(os.listdir(internal)))
for f in sorted(os.listdir(internal)):
    full = os.path.join(internal, f)
    sz = "" if os.path.isdir(full) else os.path.getsize(full)
    mark = " <<<" if ("pyz" in f.lower() or "python312" in f or "base_library" in f) else ""
    out.append("  %s %s %s%s" % ("DIR" if os.path.isdir(full) else "FILE", f, sz, mark))

# 查找所有 pyz
out.append("\n=== 所有 .pyz 文件 ===")
for root2, dirs, files in os.walk(root):
    for f in files:
        if f.lower().endswith(".pyz"):
            out.append("  %s (%dB)" % (os.path.join(root2, f), os.path.getsize(os.path.join(root2, f))))

with open(r"D:\7tan\7tanAI\_structure.txt", "w", encoding="utf-8") as fh:
    fh.write("\n".join(out))
print("ok")
