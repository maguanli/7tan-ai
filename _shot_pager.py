# -*- coding: utf-8 -*-
import os, subprocess, sys, glob
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
from PIL import Image

cands = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
         r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
         r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
         r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"]
CHROME = next((p for p in cands if os.path.exists(p)), None)
print('browser =', CHROME)
if not CHROME:
    for pat in [r"C:\**\chrome.exe"]:
        g = glob.glob(pat, recursive=False)
        print('glob', g[:5])
    sys.exit(1)

OUT = Path(r"D:\7tan\7tanAI\data\pager_shots")
OUT.mkdir(parents=True, exist_ok=True)

jobs = [
    ("p1_mobile",  "https://www.7tan.com/bbs/user/1/",      390, 2700),
    ("p2_mobile",  "https://www.7tan.com/bbs/user/1_2/",    390, 2700),
    ("p23_mobile", "https://www.7tan.com/bbs/user/1_23/",   390, 2000),
    ("p2_desktop", "https://www.7tan.com/bbs/user/1_2/",    1280, 2000),
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
        print("%-12s 失败" % name)
print('dir =', OUT)
