# -*- coding: utf-8 -*-
import io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
L = open(r"app\crawler.py", encoding="utf-8").read().splitlines()
KEYS = ["续抓", "resume", "_load", "_restore", "pages_total", "max_pages", "已达", "def _", "def run"]
for i, l in enumerate(L):
    if any(k in l for k in KEYS):
        print("%4d | %s" % (i + 1, l.rstrip()))
