# -*- coding: utf-8 -*-
"""点击微信输入框并粘贴消息"""
import sys, time
sys.stdout.reconfigure(encoding='utf-8')
import pyautogui
import pyperclip
import mss
from PIL import Image

# 点击输入框
input_x, input_y = 800, 800
print('clicking input box at', input_x, input_y)
pyautogui.click(input_x, input_y)
time.sleep(0.8)

# 输入问候语
msg = "兵龙哥，晚上好！我是7Tan的AI，正在测试桌面机器人自动发消息功能😄 你聊的机器人话题很有意思，7Tan刚升级了视觉，现在能看懂屏幕了，改天给你演示！"
pyperclip.copy(msg)
pyautogui.hotkey('ctrl', 'v')
time.sleep(0.8)

# 截图验证输入框内容
with mss.mss() as sct:
    monitor = sct.monitors[1]
    img = sct.grab(monitor)
    pil = Image.frombytes('RGB', img.size, img.rgb)
    pil.save('data/screenshots/wechat_input_check.png')
    print('saved input check')
