# -*- coding: utf-8 -*-
"""把微信窗口设为置顶(TOPMOST)，防止被其他窗口遮挡；支持取消置顶"""
import ctypes, sys, time
from ctypes import wintypes
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

user32 = ctypes.windll.user32
HWND = 1313304  # 微信主窗口
HWND_TOPMOST = -1
HWND_NOTOPMOST = -2
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040

topmost = len(sys.argv) < 2 or sys.argv[1] != 'off'
flag = HWND_TOPMOST if topmost else HWND_NOTOPMOST

user32.ShowWindow(HWND, 9)  # SW_RESTORE
time.sleep(0.2)
# 置顶/取消置顶
user32.SetWindowPos(HWND, flag, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW)
time.sleep(0.3)
try:
    user32.SetForegroundWindow(HWND)
except Exception:
    pass
time.sleep(0.3)

# 验证
visible = user32.IsWindowVisible(HWND)
rect = wintypes.RECT()
user32.GetWindowRect(HWND, ctypes.byref(rect))
# 检查是否 TOPMOST
GW_EXSTYLE = -20
exstyle = user32.GetWindowLongW(HWND, GW_EXSTYLE)
is_topmost = bool(exstyle & 0x00000008)  # WS_EX_TOPMOST
print(f'visible={visible} topmost={is_topmost} rect=({rect.left},{rect.top},{rect.right-rect.left}x{rect.bottom-rect.top})')
print('DONE')
