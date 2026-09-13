# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8")
import pygetwindow as gw

for w in gw.getAllWindows():
    t = (w.title or "").strip()
    if t:
        print(f"{t[:50]!r}  pos=({w.left},{w.top},{w.width}x{w.height})  visible={w.visible} active={w.isActive}")
