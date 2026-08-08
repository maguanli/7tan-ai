# -*- coding: utf-8 -*-
"""按之前成功经验：关闭多余窗口→激活1443834→点击输入框→粘贴→截图验证（不发送）"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import pyperclip

user32 = ctypes.windll.user32
WM_CLOSE = 0x0010

# 1. 关闭多余窗口（清掉误粘内容 + 避免遮挡）
for hwnd in [133662, 3672392]:
    if user32.IsWindow(hwnd):
        user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        print(f'已关闭 hwnd={hwnd}')
    else:
        print(f'hwnd={hwnd} 不存在')
time.sleep(2)

# 2. 激活目标群窗口 1443834
QQ_HWND = 1443834
user32.ShowWindow(QQ_HWND, 9)  # SW_RESTORE
time.sleep(0.2)
user32.SetWindowPos(QQ_HWND, -1, 0, 0, 0, 0, 0x0001 | 0x0002 | 0x0010)  # TOPMOST
user32.SetForegroundWindow(QQ_HWND)
time.sleep(0.6)

fg = user32.GetForegroundWindow()
print(f'前台窗口: {fg} (目标={QQ_HWND}, 匹配={fg == QQ_HWND})')

# 3. 点击输入框（之前验证过的坐标）
pyautogui.click(1000, 765)
time.sleep(0.6)

# 4. 粘贴中文消息
MSG = ("🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！\n"
       "🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布到7坛，一条龙自动化\n"
       "🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答\n"
       "⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行\n"
       "以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏")

pyperclip.copy(MSG)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(1.0)

# 5. 立即截图输入框区域（同之前验证区域 850,700,540,140）
img = pyautogui.screenshot(region=(850, 700, 540, 140))
img.save(r'D:\7tan\7tanAI\scripts\qq_input_after_paste.png')
print('已截图输入框 -> qq_input_after_paste.png')

# 6. 验证输入框是否有内容（深色像素）
from PIL import Image
gray = img.convert('L')
dark = sum(1 for p in gray.getdata() if p < 128)
print(f'输入框深色像素: {dark} ({dark / (img.width * img.height) * 100:.2f}%)')

# 7. 全窗口截图用于确认上下文
img2 = pyautogui.screenshot(region=(480, 200, 1060, 640))
img2.save(r'D:\7tan\7tanAI\scripts\qq_win_after_paste.png')
print('已截图全窗口 -> qq_win_after_paste.png')
