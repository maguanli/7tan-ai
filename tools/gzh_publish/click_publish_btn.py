# -*- coding: utf-8 -*-
"""点击弹窗中的发表确认按钮(458,456)，等待后截图验证"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import mss
from PIL import Image

def foreground(hwnd):
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 9)
    time.sleep(0.3)
    user32.SetForegroundWindow(hwnd)
    time.sleep(1.0)

def main():
    foreground(132302)
    # 点击弹窗"发表"按钮（全屏坐标）
    pyautogui.click(458, 456)
    time.sleep(5.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_click_publish_btn.png')
        print('saved after_click_publish_btn.png')

if __name__ == '__main__':
    main()
