# -*- coding: utf-8 -*-
"""获取7Tan窗口矩形位置，并输出当前鼠标位置"""
import sys, io, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from ctypes import wintypes

user32 = ctypes.windll.user32

class RECT(ctypes.Structure):
    _fields_ = [('left', wintypes.LONG), ('top', wintypes.LONG),
                ('right', wintypes.LONG), ('bottom', wintypes.LONG)]

def main():
    hwnd = 132302
    rect = RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    print('7Tan window rect: L=%d T=%d R=%d B=%d (W=%d H=%d)' % (
        rect.left, rect.top, rect.right, rect.bottom,
        rect.right - rect.left, rect.bottom - rect.top))
    # 浏览器标签位置：之前 click_browser_tab.py 点击 (338,49) 是"浏览器"标签
    # 打印所有可见窗口rect帮助确认
    print('--- all windows ---')

if __name__ == '__main__':
    main()
