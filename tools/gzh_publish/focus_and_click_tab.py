# -*- coding: utf-8 -*-
"""聚焦7Tan主窗口→点击'浏览器'标签→截屏验证"""
import sys, io, time, ctypes
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pyautogui
import mss
from PIL import Image
from ctypes import wintypes

user32 = ctypes.windll.user32
HWND = 132302  # 7Tan — AI工具

def main():
    # 显示并聚焦窗口
    user32.ShowWindow(HWND, 9)  # SW_RESTORE
    time.sleep(0.3)
    user32.SetForegroundWindow(HWND)
    time.sleep(0.8)
    # 点击浏览器标签（尝试多个y坐标，从y=35到60，点文字中心上方一点）
    for y in (40, 49, 58):
        pyautogui.click(338, y)
        time.sleep(0.6)
    # 截屏
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_focus_click_tab.png')
        print('saved', img.size)
    print('done')

if __name__ == '__main__':
    main()
