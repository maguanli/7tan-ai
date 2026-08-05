# -*- coding: utf-8 -*-
"""点击微信顶部搜索框并输入关键词"""
import sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui, pygetwindow as gw

# 激活微信
wins = gw.getWindowsWithTitle('微信')
if not wins:
    print('未找到微信窗口')
    sys.exit(1)
w = wins[0]
w.activate()
time.sleep(0.8)

# 1. 点击搜索框（猜测位置 x=180, y=48），若无效再试几个位置
for x, y in [(180, 48), (220, 48), (150, 48), (100, 48), (250, 48)]:
    pyautogui.click(x, y)
    time.sleep(0.6)
    # 截图顶部看是否有输入框出现
    img = pyautogui.screenshot(region=(0, 0, 800, 110))
    img.save(r"D:\7tan\7tanAI\after_click.png")
    time.sleep(0.3)

# 2. 输入关键词
pyautogui.typewrite('youxi', interval=0.05)  # 先用拼音? 不, 直接输入中文需要剪贴板
