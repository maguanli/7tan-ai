import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
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
for h, t, r in wins:
    if 'QQ' in t or '7723' in t or '游戏' in t or '群' in t or t == '7Tan' or '7Tan' in t:
        print(f'{h} | {r} | {t!r}')
print('---ALL---')
for h, t, r in wins:
    print(f'{h} | {r} | {t!r}')
