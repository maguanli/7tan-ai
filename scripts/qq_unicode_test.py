# -*- coding: utf-8 -*-
"""用 SendInput Unicode 注入中文测试（绕过剪贴板）"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from PIL import Image
import psutil

user32 = ctypes.windll.user32

# --- SendInput 定义 ---
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_UNICODE = 0x0004

class KEYBDINPUT(ctypes.Structure):
    _fields_ = [('wVk', wt.WORD), ('wScan', wt.WORD), ('dwFlags', wt.DWORD),
                ('time', wt.DWORD), ('dwExtraInfo', ctypes.POINTER(ctypes.c_ulong))]

class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [('ki', KEYBDINPUT), ('mi', ctypes.c_byte * 8)]
    _anonymous_ = ('_input',)
    _fields_ = [('type', wt.DWORD), ('_input', _INPUT)]

def send_unicode_char(ch):
    """发送单个Unicode字符（含代理对处理）"""
    inputs = []
    for unit in ch.encode('utf-16-le'):
        pass
    # 用 utf-16 code units
    code_units = []
    for u in ch:
        cp = ord(u)
        if 0x10000 <= cp <= 0x10FFFF:
            cp -= 0x10000
            code_units.append(0xD800 + (cp >> 10))
            code_units.append(0xDC00 + (cp & 0x3FF))
        else:
            code_units.append(cp)
    for cu in code_units:
        ki = KEYBDINPUT(0, cu, KEYEVENTF_UNICODE, 0, None)
        inp = INPUT(INPUT_KEYBOARD, ki)
        user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))
        ki2 = KEYBDINPUT(0, cu, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP, 0, None)
        inp2 = INPUT(INPUT_KEYBOARD, ki2)
        user32.SendInput(1, ctypes.byref(inp2), ctypes.sizeof(INPUT))
        time.sleep(0.01)

def send_text(text):
    for ch in text:
        send_unicode_char(ch)
        time.sleep(0.02)

# --- 找QQ窗口 ---
def find_qq_windows():
    wins = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def enum_cb(h, lp):
        if not user32.IsWindowVisible(h):
            return True
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        try:
            import psutil as ps
            if ps.Process(p.value).name().lower() != 'qq.exe':
                return True
        except Exception:
            return True
        cls = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(h, cls, 256)
        if not cls.value.startswith('Chrome_WidgetWin'):
            return True
        r = wt.RECT()
        user32.GetWindowRect(h, ctypes.byref(r))
        w, hh = r.right - r.left, r.bottom - r.top
        if w > 300 and hh > 300:
            wins.append((h, r.left, r.top, w, hh))
        return True
    user32.EnumWindows(enum_cb, 0)
    return wins

wins = find_qq_windows()
if not wins:
    print('未找到QQ窗口')
    sys.exit(1)
QQ_HWND = max(wins, key=lambda x: x[3]*x[4])[0]
print(f'QQ窗口: {QQ_HWND}')

user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)
fg = user32.GetForegroundWindow()
print(f'前台: {fg} (期望 {QQ_HWND})')
if fg != QQ_HWND:
    print('前台不是QQ，中止')
    sys.exit(1)

# 点击输入框区域（探测成功的点附近）
pyautogui.click(1000, 800)
time.sleep(0.5)

# 清空（如果之前有残留a）
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.press('delete')
time.sleep(0.3)

# 发送测试中文
test_text = '测试中文输入Test123'
print(f'发送测试: {test_text}')
send_text(test_text)
time.sleep(0.8)

# 截图
img = pyautogui.screenshot(region=(500, 770, 800, 60))
img.save(r'D:\7tan\7tanAI\scripts\qq_unicode_test.png')
print('已截图 qq_unicode_test.png')
