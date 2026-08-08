# -*- coding: utf-8 -*-
"""尝试在QQ主面板切换到聊天模式：点击右侧消息预览区域"""
import ctypes
import ctypes.wintypes as wt
import sys
import time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import pyautogui
from rapidocr_onnxruntime import RapidOCR
import numpy as np

user32 = ctypes.windll.user32

# 点击右侧消息预览区域多个位置
for (x, y) in [(900, 500), (1000, 400), (900, 300), (1100, 600)]:
    pyautogui.click(x, y)
    time.sleep(0.8)
    # 检查底部是否有输入框（截图+OCR）
    img = pyautogui.screenshot(region=(480, 700, 1060, 140))
    eng = RapidOCR()
    result, _ = eng(np.array(img))
    texts = [t for b, t, s in (result or [])]
    has_input = any(('输入' in t or '回复' in t or '发送' in t) for t in texts)
    print(f'点击({x},{y}): 底部文字={texts[:3]}... 发送按钮存在={has_input}')
    if has_input:
        print('!!! 检测到聊天输入界面 !!!')
        img.save(r'D:\7tan\7tanAI\scripts\qq_chat_mode.png')
        break
