# -*- coding: utf-8 -*-
import subprocess, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
G = r"D:\7tan\7tanAI\tools\gzh_publish\gzh_do.py"
args = [sys.executable, G, "fill-form",
        "--title", "《贪吃蛇大作战》测评：榜一36万，我只有106",
        "--author", "老马",
        "--title_pos", "820,310",
        "--author_pos", "766,344"]
p = subprocess.run(args, capture_output=True)
print(p.stdout.decode('utf-8', 'replace'))
print('--STDERR--')
print(p.stderr.decode('utf-8', 'replace'))
print('--RC--', p.returncode)
