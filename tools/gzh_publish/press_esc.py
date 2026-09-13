# -*- coding: utf-8 -*-
"""按Esc关闭弹层，截图看状态"""
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
    time.sleep(0.8)

def main():
    foreground(132302)
    pyautogui.press('esc')
    time.sleep(3.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_esc.png')
        print('saved after_esc.png')

if __name__ == '__main__':
    main()
