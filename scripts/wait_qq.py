# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import time
import pygetwindow as gw

print('等待 QQ 窗口出现...')
for i in range(12):
    wins = [w for w in gw.getAllTitles() if w.strip()]
    qq_wins = [w for w in wins if 'QQ' in w or 'qq' in w or '登录' in w or 'Login' in w or '7723' in w]
    print(f'[{i*3}s] 窗口数={len(wins)} QQ窗口={qq_wins}')
    if qq_wins:
        break
    time.sleep(3)

print('=== 全部窗口 ===')
for w in wins:
    print(repr(w))
