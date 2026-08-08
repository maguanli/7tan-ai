# -*- coding: utf-8 -*-
"""动态查找QQ聊天窗口 → 置顶 → 粘贴消息（不发送）"""
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

def find_qq_windows():
    """返回所有尺寸>300x300的QQ Chrome_WidgetWin_1 窗口"""
    wins = []
    @ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
    def enum_cb(h, lp):
        if not user32.IsWindowVisible(h):
            return True
        p = wt.DWORD()
        user32.GetWindowThreadProcessId(h, ctypes.byref(p))
        try:
            proc = psutil.Process(p.value)
            if proc.name().lower() != 'qq.exe':
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

# 1. 找QQ窗口
wins = find_qq_windows()
print(f'QQ大窗口: {wins}')
if not wins:
    print('未找到QQ窗口！')
    sys.exit(1)

# 取最大的（聊天窗口）
QQ_HWND = max(wins, key=lambda x: x[3]*x[4])[0]
print(f'使用QQ窗口: {QQ_HWND}')

# 2. 置顶+前台（重试3次）
ok = False
for attempt in range(3):
    user32.ShowWindow(QQ_HWND, 9)
    time.sleep(0.2)
    user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
    user32.SetForegroundWindow(QQ_HWND)
    time.sleep(0.5)
    fg = user32.GetForegroundWindow()
    print(f'  尝试{attempt+1}: 前台={fg}')
    if fg == QQ_HWND:
        ok = True
        break
    # 前台可能是新重建的QQ窗口（HWND变了），重新查找
    wins = find_qq_windows()
    if wins:
        QQ_HWND = max(wins, key=lambda x: x[3]*x[4])[0]
        print(f'  QQ HWND 更新为: {QQ_HWND}')

if not ok:
    print('无法获得QQ前台焦点，中止')
    sys.exit(1)

print('QQ 已在前台 ✓')

# 3. 点击输入框 (1000,800) + 清空 + 粘贴
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
img.save(r'D:\7tan\7tanAI\scripts\qq_final_input4.png')
img2 = pyautogui.screenshot(region=(480, 200, 1060, 640))
img2.save(r'D:\7tan\7tanAI\scripts\qq_final_win4.png')
print('截图完成: qq_final_input4.png / qq_final_win4.png')

gray = img.convert('L')
dark = sum(1 for p in gray.getdata() if p < 128)
print(f'输入框深色: {dark/(gray.width*gray.height)*100:.2f}%')
