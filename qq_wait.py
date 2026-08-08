import sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# 等 15 秒再查
time.sleep(15)

out = subprocess.run(['tasklist'], capture_output=True, text=True, timeout=30)
qq_lines = [l for l in out.stdout.splitlines() if 'QQ' in l.upper() or 'qq' in l.lower()]
print('=== QQ processes ===')
for l in qq_lines[:20]:
    print(l)

import win32gui
wins = []
def cb(hwnd, extra):
    if win32gui.IsWindowVisible(hwnd):
        t = win32gui.GetWindowText(hwnd)
        if t.strip():
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception:
                rect = None
            wins.append((hwnd, t.strip(), rect))
win32gui.EnumWindows(cb, None)
print('=== QQ-like windows ===')
for h, t, r in wins:
    if 'QQ' in t or '7723' in t or '登录' in t or '游戏' in t:
        print(f'{h} | {r} | {t!r}')
