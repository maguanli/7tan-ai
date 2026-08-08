import sys, subprocess, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

exe = r'C:\Program Files\Tencent\QQNT\QQ.exe'
p = subprocess.Popen([exe], cwd=r'C:\Program Files\Tencent\QQNT')
print('launched pid', p.pid)
time.sleep(10)

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
    if 'QQ' in t or '7723' in t or '游戏' in t:
        print(f'{h} | {r} | {t!r}')
print('---')
for h, t, r in wins:
    print(f'{h} | {r} | {t!r}')
