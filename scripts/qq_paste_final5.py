# -*- coding: utf-8 -*-
"""最小化所有7Tan窗口 → QQ置顶前台 → 粘贴消息（不发送）"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import pyperclip
from PIL import Image
import psutil

user32 = ctypes.windll.user32
QQ_HWND = 395876

# 1. 找所有 7Tan(python.exe 且窗口标题含7Tan/7tan) 窗口并最小化
print('=== 最小化 7Tan 相关窗口 ===')
tans = []
for p in psutil.process_iter(['pid', 'name', 'exe']):
    try:
        if p.info['name'] and p.info['name'].lower() in ('python.exe', 'pythonw.exe'):
            tans.append(p.info['pid'])
    except Exception:
        pass

@ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
def enum_cb(hwnd, lparam):
    if not user32.IsWindowVisible(hwnd):
        return True
    pid = wt.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    if pid.value in tans:
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        rect = wt.RECT()
        user32.GetWindowRect(hwnd, ctypes.byref(rect))
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 50 and h > 50:
            user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
            print(f'  最小化: hwnd={hwnd} "{title}" {w}x{h}')
    return True

user32.EnumWindows(enum_cb, 0)
time.sleep(0.8)

# 2. QQ 置顶
user32.ShowWindow(QQ_HWND, 9)
time.sleep(0.2)
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)
fg = user32.GetForegroundWindow()
print(f'前台: {fg} (期望 {QQ_HWND}) {"✓" if fg == QQ_HWND else "✗"}')
if fg != QQ_HWND:
    print('中止：前台不是QQ')
    sys.exit(1)

# 3. 点击输入框 + 清空 + 粘贴
pyautogui.click(1000, 800)
time.sleep(0.4)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.press('delete')
time.sleep(0.4)

MSG = ("🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！\n"
       "🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布到7坛，一条龙自动化\n"
       "🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答\n"
       "⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行\n"
       "以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏")
pyperclip.copy(MSG)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)

# 4. 截图验证
img = pyautogui.screenshot(region=(500, 770, 800, 60))
img.save(r'D:\7tan\7tanAI\scripts\qq_final_input3.png')
img2 = pyautogui.screenshot(region=(480, 200, 1060, 640))
img2.save(r'D:\7tan\7tanAI\scripts\qq_final_win3.png')
print('截图完成: qq_final_input3.png / qq_final_win3.png')

gray = img.convert('L')
dark = sum(1 for p in gray.getdata() if p < 128)
print(f'输入框深色: {dark/(gray.width*gray.height)*100:.2f}%')
