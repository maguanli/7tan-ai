# -*- coding: utf-8 -*-
"""把7Tan窗口移到屏幕外 -> 微信最大化置顶 -> 截图确认"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import win32gui, win32con
import pyautogui

def enum_all():
    out = []
    def cb(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            t = win32gui.GetWindowText(hwnd)
            cls = win32gui.GetClassName(hwnd)
            out.append((hwnd, t, cls))
    win32gui.EnumWindows(cb, None)
    return out

# 1. 记录并移走 7Tan 窗口
moved = []
for hwnd, t, cls in enum_all():
    if '7Tan' in t:
        try:
            rect = win32gui.GetWindowRect(hwnd)
            print('7Tan窗口:', t, hwnd, rect)
            if rect[2] > 500 and rect[3] > 400:  # 只移主窗口
                win32gui.MoveWindow(hwnd, -10000, -10000, rect[2]-rect[0], rect[3]-rect[1], True)
                moved.append((hwnd, rect))
                print('  已移到屏幕外')
        except Exception as e:
            print('  失败', e)

time.sleep(0.8)

# 2. 微信最大化置顶
for hwnd, t, cls in enum_all():
    if '微信' in t:
        print('微信窗口:', hwnd, win32gui.GetWindowRect(hwnd))
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
        time.sleep(0.5)
        win32gui.SetForegroundWindow(hwnd)
        print('  置顶后 rect:', win32gui.GetWindowRect(hwnd))
        break

time.sleep(1.2)
img = pyautogui.screenshot()
img.save(r"D:\7tan\7tanAI\check5.png")
print('saved check5.png')

# 3. 恢复 7Tan 窗口位置（先恢复，避免影响用户）
for hwnd, rect in moved:
    try:
        win32gui.MoveWindow(hwnd, rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1], True)
        print('7Tan已恢复:', hwnd, rect)
    except Exception as e:
        print('恢复失败', hwnd, e)
