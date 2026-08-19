# -*- coding: utf-8 -*-
"""输入框已定位(1000,800)：清空测试字符 → 粘贴正式消息 → 截图验证（不发送）"""
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
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.5)
print(f'前台: {user32.GetForegroundWindow()}')

# 1. 点击输入框（正确位置）
pyautogui.click(1000, 800)
time.sleep(0.5)

# 2. 清空测试字符
pyautogui.hotkey('ctrl', 'a')
time.sleep(0.2)
pyautogui.press('delete')
time.sleep(0.4)
print('已清空输入框')

# 3. 粘贴正式消息
MSG = ("🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！\n"
       "🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布到7坛，一条龙自动化\n"
       "🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答\n"
       "⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行\n"
       "以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏")
pyperclip.copy(MSG)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)
print('已粘贴正式消息')

# 4. 截图输入框区域验证
img = pyautogui.screenshot(region=(500, 770, 800, 60))
img.save(r'D:\7tan\7tanAI\scripts\qq_final_input.png')
print('输入框截图 -> qq_final_input.png')

# 5. 全窗口截图
img2 = pyautogui.screenshot(region=(480, 200, 1060, 640))
img2.save(r'D:\7tan\7tanAI\scripts\qq_final_win.png')
print('全窗口截图 -> qq_final_win.png')
