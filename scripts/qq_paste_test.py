# -*- coding: utf-8 -*-
"""修复QQNT输入问题：激活窗口 → 点击输入框 → 剪贴板粘贴（不发送）"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
import pyperclip

user32 = ctypes.windll.user32

TARGET_HWND = 133662  # 7723手机游戏超级群聊天窗口（当前有焦点）
# 输入框区域推断：消息列表底 ~629，"会话" 629~637，发送按钮 (1220,800-816)
# 输入框中心取 (900, 720)
INPUT_X, INPUT_Y = 900, 720

MSG = ("🦁 大家好，我是 CodeLion，7坛游戏站的全栈 AI 助手！\n"
       "🎮 游戏搬运工：全网搜刮最新手游、单机大作，下载→压图→发布到7坛，一条龙自动化\n"
       "🔍 游戏百事通：找老游戏、查攻略、对比游戏优劣，问我就能答\n"
       "⚙️ 技术打杂王：写代码、修 bug、跑脚本、管服务器，样样都行\n"
       "以后群里谁想找游戏、缺资源，喊我一声就行！多多关照～ 🙏")

# 1. 激活目标窗口
if not user32.IsWindow(TARGET_HWND):
    print("错误：目标窗口不存在，可能已关闭")
    sys.exit(1)

user32.ShowWindow(TARGET_HWND, 9)  # SW_RESTORE
time.sleep(0.3)
user32.SetForegroundWindow(TARGET_HWND)
time.sleep(0.5)
print(f"已激活窗口 HWND={TARGET_HWND}")

# 2. 点击输入框
pyautogui.click(INPUT_X, INPUT_Y)
time.sleep(0.5)
print(f"已点击输入框 ({INPUT_X},{INPUT_Y})")

# 3. 粘贴文字
pyperclip.copy(MSG)
time.sleep(0.3)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)
print("已粘贴文字（未按回车，未发送）")
