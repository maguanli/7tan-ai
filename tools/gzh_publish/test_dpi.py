# -*- coding: utf-8 -*-
"""测试DPI缩放：SetCursorPos后读回实际位置"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from ctypes import wintypes

user32 = ctypes.windll.user32

class POINT(ctypes.Structure):
    _fields_ = [('x', wintypes.LONG), ('y', wintypes.LONG)]

def main():
    # 系统DPI
    try:
        dpi = ctypes.windll.shcore.GetDpiForSystem()
        print('System DPI:', dpi)
    except Exception as e:
        print('GetDpiForSystem fail:', e)
    # 测试坐标映射
    for tx, ty in [(100, 100), (455, 456), (1026, 933), (901, 929)]:
        user32.SetCursorPos(tx, ty)
        time.sleep(0.3)
        p = POINT()
        user32.GetCursorPos(ctypes.byref(p))
        print('set (%d,%d) -> get (%d,%d)' % (tx, ty, p.x, p.y))

if __name__ == '__main__':
    main()
