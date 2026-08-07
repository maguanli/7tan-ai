# -*- coding: utf-8 -*-
"""模拟鼠标滚轮滚动"""
import ctypes, time, sys

delta = int(sys.argv[1]) if len(sys.argv) > 1 else -400
ctypes.windll.user32.SetCursorPos(960, 500)
time.sleep(0.2)
# WHEEL_DELTA=120, MOUSEEVENTF_WHEEL=0x0800
ctypes.windll.user32.mouse_event(0x0800, 0, 0, delta, 0)
time.sleep(0.3)
print("SCROLLED", delta)
