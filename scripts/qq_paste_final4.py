# -*- coding: utf-8 -*-
"""最小化7Tan主窗口 → QQ置顶 → 清空输入框 → 粘贴消息 → 截图验证（不发送）"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import pyperclip
from PIL import Image

user32 = ctypes.windll.user32
QQ_HWND = 395876
TAN_HWND = 6097354  # 7Tan 主窗口

# 1. 最小化 7Tan 主窗口
user32.ShowWindow(TAN_HWND, 6)  # SW_MINIMIZE
time.sleep(0.5)
print(f'7Tan 最小化: {user32.IsIconic(TAN_HWND)}')

# 2. QQ 置顶+前台
user32.ShowWindow(QQ_HWND, 9)
time.sleep(0.2)
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)
fg = user32.GetForegroundWindow()
print(f'前台: {fg} (期望 {QQ_HWND}) {"✓" if fg == QQ_HWND else "✗"}')

if fg != QQ_HWND:
    print('前台不是QQ！中止操作，避免误操作')
    sys.exit(1)

# 3. 点击输入框并清空
pyautogui.click(1000, 800)
time.sleep(0.4)
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.press('delete')
time.sleep(0.4)

# 4. 粘贴正式消息
MSG = ("🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！\n"
       "🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布到7坛，一条龙自动化\n"
       "🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答\n"
       "⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行\n"
       "以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏")
pyperclip.copy(MSG)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)

# 5. 截图验证
img = pyautogui.screenshot(region=(500, 770, 800, 60))
img.save(r'D:\7tan\7tanAI\scripts\qq_final_input2.png')
img2 = pyautogui.screenshot(region=(480, 200, 1060, 640))
img2.save(r'D:\7tan\7tanAI\scripts\qq_final_win2.png')
print('截图完成: qq_final_input2.png / qq_final_win2.png')

# 像素分析
gray = img.convert('L')
dark = sum(1 for p in gray.getdata() if p < 128)
print(f'输入框深色: {dark/(gray.width*gray.height)*100:.2f}%')
