# -*- coding: utf-8 -*-
"""按回车确认弹窗，等待后截图"""
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
    pyautogui.press('enter')
    time.sleep(4.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_enter.png')
        print('saved after_enter.png')
    # 再按一次enter兜底
    pyautogui.press('enter')
    time.sleep(3.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_enter2.png')
        print('saved after_enter2.png')

if __name__ == '__main__':
    main()
