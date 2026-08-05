# -*- coding: utf-8 -*-
"""启动微信并监控状态"""
import sys, io, time, subprocess, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

exe = r"C:\Program Files\Tencent\Weixin\Weixin.exe"
if os.path.exists(exe):
    subprocess.Popen([exe], shell=False)
    print('微信已启动')
else:
    print('微信exe不存在:', exe)

# 等待并检查
for i in range(15):
    time.sleep(2)
    r = os.popen('tasklist | findstr /I Weixin').read()
    if 'Weixin' in r or 'Weixin.exe' in r:
        print(f'[{i*2}s] 微信进程已出现')
        break

# 检查窗口
import win32gui
def enum():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            if t.strip():
                out.append((hwnd, t))
    win32gui.EnumWindows(cb, None)
    return out

time.sleep(4)
print('=== 当前窗口 ===')
for hwnd, t in enum():
    print(hwnd, repr(t))
