import sys, ctypes, time
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import win32gui, win32con

# 最小化遮挡的全屏资源管理器窗口
h_explorer = 788328
try:
    win32gui.ShowWindow(h_explorer, win32con.SW_MINIMIZE)
    print('minimized explorer', h_explorer)
except Exception as e:
    print('explorer err:', e)

# 也把计算器等移走
for h in [197056, 131938]:
    try:
        win32gui.ShowWindow(h, win32con.SW_MINIMIZE)
        print('minimized', h)
    except Exception as e:
        print('err', h, e)

# 激活 QQ 窗口 395876 并置顶
hwnd = 395876
try:
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
    win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE | win32con.SWP_SHOWWINDOW)
    win32gui.SetWindowPos(hwnd, win32con.HWND_NOTOPMOST, 0, 0, 0, 0,
                          win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)
    win32gui.SetForegroundWindow(hwnd)
    print('QQ activated & brought to front')
except Exception as e:
    print('QQ err:', e)

time.sleep(1.2)
print('done')
