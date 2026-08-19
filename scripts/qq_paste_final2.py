# -*- coding: utf-8 -*-
"""QQ窗口已置顶：点击输入框(1000,765) → 粘贴中文消息 → 截图验证（不发送）"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import pyperclip

user32 = ctypes.windll.user32
QQ_HWND = 1443834

# 1. 确保前台
fg = user32.GetForegroundWindow()
print(f'当前前台: {fg} (目标={QQ_HWND})')
if fg != QQ_HWND:
    user32.SetForegroundWindow(QQ_HWND)
    time.sleep(0.5)

# 2. 点击输入框（之前验证过的坐标）
pyautogui.click(1000, 765)
time.sleep(0.6)

# 3. 粘贴消息
MSG = ("🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！\n"
       "🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布到7坛，一条龙自动化\n"
       "🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答\n"
       "⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行\n"
       "以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏")

pyperclip.copy(MSG)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)

# 4. 截图输入框区域验证
img = pyautogui.screenshot(region=(850, 700, 540, 140))
img.save(r'D:\7tan\7tanAI\scripts\qq_input_after_paste2.png')

from PIL import Image
gray = img.convert('L')
dark = sum(1 for p in gray.getdata() if p < 128)
print(f'输入框深色像素: {dark} ({dark / (img.width * img.height) * 100:.2f}%)')

# 5. 全窗口截图
img2 = pyautogui.screenshot(region=(480, 200, 1060, 640))
img2.save(r'D:\7tan\7tanAI\scripts\qq_win_after_paste2.png')
print('截图完成：qq_input_after_paste2.png / qq_win_after_paste2.png')
