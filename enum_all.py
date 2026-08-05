# -*- coding: utf-8 -*-
"""枚举所有可见窗口"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui

def cb(hwnd, _):
    if win32gui.IsWindowVisible(hwnd):
        t = win32gui.GetWindowText(hwnd)
        if t.strip():
            try:
                rect = win32gui.GetWindowRect(hwnd)
                print(f"{hwnd} {t[:50]!r} cls={win32gui.GetClassName(hwnd)[:25]} rect={rect}")
            except Exception:
                pass

win32gui.EnumWindows(cb, None)
