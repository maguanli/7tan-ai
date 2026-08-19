# -*- coding: utf-8 -*-
"""统一截图目录：迁移根目录散落截图 + downloads/screenshots -> data/screenshots"""
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(r"D:\7tan\7tanAI")
dest = root / "data" / "screenshots"
dest.mkdir(parents=True, exist_ok=True)

root_imgs = [
    "desktop.png", "desktop_small.png", "q1_before.png", "q2_click.png", "q3_enter.png",
    "qq_activated.png", "qq_after_send.png", "qq_bottom_full.png", "qq_crop.png", "qq_crop_bw.png",
    "qq_current.png", "qq_full_now.png", "qq_input_area.png", "qq_opened.png",
    "qq_screen_current.png", "qq_win.png", "search_crop.png", "search_result.png",
    "startmenu.png", "taskbar.png", "taskbar_now.png", "taskbar_small.png",
]
moved = 0
for f in root_imgs:
    p = root / f
    if p.exists():
        shutil.move(str(p), str(dest / f))
        moved += 1
        print("Moved:", f)

src = root / "downloads" / "screenshots"
if src.exists():
    n = 0
    for item in src.iterdir():
        shutil.move(str(item), str(dest / item.name))
        n += 1
    shutil.rmtree(src)
    print("Moved downloads/screenshots/* :", n, "items")

print("=== data/screenshots total:", len(list(dest.glob("*"))))
print("=== root remaining png:", [p.name for p in root.glob("*.png")])
print("=== root remaining jpg:", [p.name for p in root.glob("*.jpg")])
print("=== downloads/screenshots exists:", (root / "downloads" / "screenshots").exists())
