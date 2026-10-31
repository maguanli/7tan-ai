# -*- coding: utf-8 -*-
"""用本地 Chrome 无头模式直接截线上页面：手机宽 390 / 桌面宽 1280"""
import os, subprocess, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
OUT = Path(r"D:\7tan\7tanAI\data\profile_shots")
OUT.mkdir(parents=True, exist_ok=True)

jobs = [
    ("p1_mobile",  "https://www.7tan.com/bbs/user/1/",          390, 2600),
    ("p1_desktop", "https://www.7tan.com/bbs/user/1/",          1280, 1900),
    ("p2_mobile",  "https://www.7tan.com/bbs/user/1/?page=2",   390, 2600),
    ("p23_mobile", "https://www.7tan.com/bbs/user/1/?page=23",  390, 2000),
    ("single",     "https://www.7tan.com/bbs/user/1689/",       390, 1400),
]

for name, url, w, h in jobs:
    shot = OUT / (name + ".png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                    "--virtual-time-budget=12000",
                    "--window-size=%d,%d" % (w, h),
                    "--screenshot=" + str(shot), url],
                   capture_output=True, timeout=120)
    if shot.exists():
        im = Image.open(shot)
        print("%-12s %s  %dx%d" % (name, url, im.size[0], im.size[1]))
    else:
        print("%-12s 截图失败" % name)

print("\n目录:", OUT)
