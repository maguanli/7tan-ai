# -*- coding: utf-8 -*-
import sys, time
sys.stdout.reconfigure(encoding="utf-8")
import pygetwindow as gw

block_kw = ["PowerShell", "记事本", "计算器", "Cloud Code", "Google Chrome", "Chrome", "cmd", "CMD"]
minimized = []
for w in gw.getAllWindows():
    t = (w.title or "").strip()
    if not t or "7Tan" in t:
        continue
    if any(k in t for k in block_kw):
        try:
            w.minimize()
            minimized.append(t[:40])
        except Exception as e:
            print("minimize fail:", t[:40], e)

print("minimized:", minimized)

# 激活 7Tan 主窗口
for w in gw.getAllWindows():
    if "7Tan" in (w.title or ""):
        try:
            w.activate()
            print("activated:", w.title)
        except Exception as e:
            print("activate fail:", e)
time.sleep(1.2)

# 再列出可见窗口确认
for w in gw.getAllWindows():
    t = (w.title or "").strip()
    if t and w.visible:
        print(f"visible: {t[:40]!r} ({w.left},{w.top},{w.width}x{w.height})")
print("done")
