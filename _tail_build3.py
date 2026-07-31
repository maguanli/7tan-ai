# -*- coding: utf-8 -*-
import os, subprocess

p = r"D:\7tan\7tanAI\dist\build_verify_log.txt"
data = open(p, "rb").read()
text = data.decode("utf-8", errors="replace")
lines = [l for l in text.splitlines() if l.strip()]

out = []
out.append("lines: %d" % len(lines))
out.append("--- last 8 ---")
for l in lines[-8:]:
    out.append(l[:200])

r = subprocess.run(["tasklist", "/FI", "PID eq 1940"], capture_output=True, text=True, encoding="utf-8", errors="replace")
alive = "1940" in r.stdout
out.append("pyinstaller alive: %s" % alive)

# 检查 PYZ.pyz 是否已生成
pyz = r"D:\7tan\7tanAI\dist\7tan-editor\_internal\PYZ.pyz"
out.append("PYZ.pyz exists: %s" % os.path.exists(pyz))

with open(r"D:\7tan\7tanAI\_tail_out2.txt", "w", encoding="utf-8") as f:
    f.write("\n".join(out))
print("ok")
