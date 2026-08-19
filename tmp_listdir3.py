# -*- coding: utf-8 -*-
import os

out = []
for root in ('C:/', 'D:/'):
    out.append(f"=== {root} ===")
    try:
        for d in sorted(os.listdir(root)):
            p = os.path.join(root, d)
            if os.path.isdir(p) and not d.isascii():
                out.append(f"DIR: {d}")
                try:
                    for f in sorted(os.listdir(p))[:60]:
                        out.append(f"    FILE/SUB: {f}")
                except Exception as e:
                    out.append(f"    ERR: {e}")
    except Exception as e:
        out.append(f"ERR: {e}")

with open(r'D:\7tan\7tanAI\tmp_dirs.txt', 'w', encoding='utf-8') as fp:
    fp.write('\n'.join(out))
print("written", len(out))
