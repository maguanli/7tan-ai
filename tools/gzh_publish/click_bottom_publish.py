# -*- coding: utf-8 -*-
"""Esc关闭弹层 -> 点击底部发表按钮(1040,935) -> 截图验证"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import mss
from PIL import Image

def main():
    user32 = ctypes.windll.user32
    user32.ShowWindow(132302, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(132302)
    time.sleep(1.0)
    # 先Esc关闭弹层
    pyautogui.press('esc')
    time.sleep(2.0)
    # 点击发表按钮
    pyautogui.click(1040, 935)
    time.sleep(5.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_bottom_publish.png')
        print('saved after_bottom_publish.png')

if __name__ == '__main__':
    main()
