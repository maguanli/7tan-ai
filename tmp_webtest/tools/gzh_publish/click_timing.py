# -*- coding: utf-8 -*-
"""点击弹层定时发表菜单项(490,617)，截图看反应"""
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
    pyautogui.click(490, 617)
    time.sleep(4.0)
    with mss.mss() as sct:
        img = sct.grab(sct.monitors[1])
        img = Image.frombytes('RGB', img.size, img.rgb)
        img.save('data/screenshots/after_timing_click.png')
        print('saved after_timing_click.png')

if __name__ == '__main__':
    main()
