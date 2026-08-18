# -*- coding: utf-8 -*-
import sys, io, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
ctypes.windll.shcore.SetProcessDpiAwareness(1)
import win32gui

fg = win32gui.GetForegroundWindow()
print('FG:', fg, repr(win32gui.GetWindowText(fg)), win32gui.GetClassName(fg))
print('WX exists:', win32gui.IsWindow(657102), 'visible:', win32gui.IsWindowVisible(657102), 'iconic:', win32gui.IsIconic(657102))
try:
    print('WX rect:', win32gui.GetWindowRect(657102))
except Exception as e:
    print('WX rect err:', e)
print('WX topmost:', bool(win32gui.GetWindowLong(657102, -8) & 0x8))
